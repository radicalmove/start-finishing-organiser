use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::{build_router, AppState};
use tower::ServiceExt;

async fn test_app() -> axum::Router {
    let pool = connect(&DbConfig::new("sqlite::memory:"))
        .await
        .expect("connect test db");
    run_migrations(&pool).await.expect("migrate test db");
    build_router(AppState::new(pool))
}

async fn request_json(
    app: axum::Router,
    method: Method,
    uri: &str,
    body: Value,
) -> (StatusCode, Value) {
    let response = app
        .oneshot(
            Request::builder()
                .method(method)
                .uri(uri)
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .expect("request"),
        )
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

#[tokio::test]
async fn global_search_finds_active_records_and_opts_into_recycle_bin() {
    let app = test_app().await;

    let (project_status, _project) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        json!({
            "title": "Renew passport project",
            "description": "Collect travel paperwork",
            "category": "personal"
        }),
    )
    .await;
    assert_eq!(project_status, StatusCode::CREATED);

    let (task_status, _task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Renew passport"}),
    )
    .await;
    assert_eq!(task_status, StatusCode::CREATED);

    let (waiting_status, _waiting) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/waiting",
        json!({
            "description": "Passport office reply",
            "person": "Case officer"
        }),
    )
    .await;
    assert_eq!(waiting_status, StatusCode::CREATED);

    let (recycle_capture_status, recycle_task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Passport duplicate"}),
    )
    .await;
    assert_eq!(recycle_capture_status, StatusCode::CREATED);
    let recycle_task_id = recycle_task["id"].as_str().expect("recycle task id");
    let (recycle_status, _recycled) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/inbox/{recycle_task_id}/recycle"),
        Value::Null,
    )
    .await;
    assert_eq!(recycle_status, StatusCode::OK);

    let (status, body) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/search?q=passport",
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["query"], "passport");
    assert_eq!(body["include_recycle_bin"], false);
    let default_items = body["items"].as_array().expect("default search items");
    assert!(default_items
        .iter()
        .any(|item| item["kind"] == "project" && item["title"] == "Renew passport project"));
    assert!(default_items
        .iter()
        .any(|item| item["kind"] == "task" && item["title"] == "Renew passport"));
    assert!(default_items
        .iter()
        .any(|item| item["kind"] == "waiting" && item["title"] == "Passport office reply"));
    assert!(!default_items
        .iter()
        .any(|item| item["recycled"].as_bool().unwrap_or(false)));

    let (status, body) = request_json(
        app,
        Method::GET,
        "/api/v1/search?q=passport&include_recycle_bin=true",
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["include_recycle_bin"], true);
    assert!(body["items"].as_array().unwrap().iter().any(|item| {
        item["kind"] == "recycle_bin"
            && item["title"] == "Passport duplicate"
            && item["recycled"] == true
    }));
}
