use axum::body::Body;
use axum::http::{header, Method, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use sfo_core::{
    PluginId, PluginSuggestionCreate, PluginSuggestionKind, PluginSuggestionPriority, PluginUpdate,
};
use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::{build_router, AppState};
use sfo_services::PluginService;
use tower::ServiceExt;

async fn test_pool() -> sqlx::SqlitePool {
    let pool = connect(&DbConfig::new("sqlite::memory:"))
        .await
        .expect("connect test db");
    run_migrations(&pool).await.expect("migrate test db");
    pool
}

async fn request_json(
    app: axum::Router,
    method: Method,
    uri: &str,
    token: Option<&str>,
    body: Value,
) -> (StatusCode, Value) {
    let mut builder = Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json");
    if let Some(token) = token {
        builder = builder.header(header::AUTHORIZATION, format!("Bearer {token}"));
    }

    let response = app
        .oneshot(builder.body(Body::from(body.to_string())).expect("request"))
        .await
        .expect("response");

    let status = response.status();
    let bytes = response
        .into_body()
        .collect()
        .await
        .expect("collect body")
        .to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("json body")
    };

    (status, json)
}

fn health_prompt_suggestion() -> PluginSuggestionCreate {
    PluginSuggestionCreate {
        plugin_id: PluginId::from("health"),
        kind: PluginSuggestionKind::HealthPrompt,
        title: "Plan a recovery walk".to_string(),
        summary: Some("A short recovery walk would fit today.".to_string()),
        detail: None,
        payload_json: "{}".to_string(),
        source_label: Some("Health".to_string()),
        source_uri: None,
        confidence: Some(0.8),
        priority: PluginSuggestionPriority::Normal,
    }
}

fn task_suggestion() -> PluginSuggestionCreate {
    PluginSuggestionCreate {
        plugin_id: PluginId::from("health"),
        kind: PluginSuggestionKind::Task,
        title: "Add workout task".to_string(),
        summary: None,
        detail: None,
        payload_json:
            r#"{"verb_noun":"Log workout","description":"From Health","when_bucket":"today"}"#
                .to_string(),
        source_label: Some("Health".to_string()),
        source_uri: None,
        confidence: None,
        priority: PluginSuggestionPriority::High,
    }
}

#[tokio::test]
async fn plugins_can_be_listed_fetched_and_enabled() {
    let app = build_router(AppState::new(test_pool().await));

    let (list_status, list) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/plugins",
        None,
        Value::Null,
    )
    .await;
    assert_eq!(list_status, StatusCode::OK);
    assert!(list
        .as_array()
        .expect("plugin list")
        .iter()
        .any(|plugin| plugin["id"] == "health"));
    assert!(list
        .as_array()
        .expect("plugin list")
        .iter()
        .any(|plugin| plugin["id"] == "communications"));

    let (get_status, health) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/plugins/health",
        None,
        Value::Null,
    )
    .await;
    assert_eq!(get_status, StatusCode::OK);
    assert_eq!(health["id"], "health");
    assert_eq!(health["enabled"], false);

    let (update_status, updated) = request_json(
        app,
        Method::PATCH,
        "/api/v1/plugins/health",
        None,
        json!({"enabled": true}),
    )
    .await;
    assert_eq!(update_status, StatusCode::OK);
    assert_eq!(updated["id"], "health");
    assert_eq!(updated["enabled"], true);
    assert_eq!(updated["status"], "ready");
}

#[tokio::test]
async fn plugin_suggestions_can_be_reviewed_dismissed_and_approved() {
    let pool = test_pool().await;
    let app = build_router(AppState::new(pool.clone()));
    let service = PluginService::new(pool);
    service.seed_builtin_plugins().await.expect("seed plugins");
    service
        .update_plugin(
            PluginId::from("health"),
            PluginUpdate {
                enabled: Some(true),
                ..PluginUpdate::default()
            },
        )
        .await
        .expect("enable health");

    let dismissible = service
        .create_suggestion(health_prompt_suggestion())
        .await
        .expect("create prompt suggestion");
    let approvable = service
        .create_suggestion(task_suggestion())
        .await
        .expect("create task suggestion");

    let (list_status, list) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/plugins/suggestions",
        None,
        Value::Null,
    )
    .await;
    assert_eq!(list_status, StatusCode::OK);
    assert_eq!(list.as_array().expect("suggestions").len(), 2);

    let (get_status, fetched) = request_json(
        app.clone(),
        Method::GET,
        &format!("/api/v1/plugins/suggestions/{}", dismissible.id),
        None,
        Value::Null,
    )
    .await;
    assert_eq!(get_status, StatusCode::OK);
    assert_eq!(fetched["id"], dismissible.id.to_string());
    assert_eq!(fetched["status"], "pending");

    let (dismiss_status, dismissed) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/plugins/suggestions/{}/dismiss", dismissible.id),
        None,
        Value::Null,
    )
    .await;
    assert_eq!(dismiss_status, StatusCode::OK);
    assert_eq!(dismissed["status"], "dismissed");

    let (approve_status, approved) = request_json(
        app,
        Method::POST,
        &format!("/api/v1/plugins/suggestions/{}/approve", approvable.id),
        None,
        Value::Null,
    )
    .await;
    assert_eq!(approve_status, StatusCode::OK);
    assert_eq!(approved["status"], "approved");
    assert_eq!(approved["created_core_kind"], "task");
    assert!(approved["created_core_id"].as_str().is_some());
}

#[tokio::test]
async fn plugin_routes_require_auth_when_token_configured() {
    let app = build_router(AppState::new(test_pool().await).with_api_token("secret-token"));

    let (missing_status, missing_body) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/plugins",
        None,
        Value::Null,
    )
    .await;
    assert_eq!(missing_status, StatusCode::UNAUTHORIZED);
    assert_eq!(missing_body["detail"], "missing or invalid API token");

    let (ok_status, body) = request_json(
        app,
        Method::GET,
        "/api/v1/plugins",
        Some("secret-token"),
        Value::Null,
    )
    .await;
    assert_eq!(ok_status, StatusCode::OK);
    assert!(body.as_array().expect("plugin list").len() >= 2);
}
