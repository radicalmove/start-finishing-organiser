use axum::body::Body;
use axum::http::{header, Method, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::{build_router, AppState};
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

#[tokio::test]
async fn health_exercise_week_normalizes_to_monday() {
    let app = build_router(AppState::new(test_pool().await));

    let (status, week) = request_json(
        app,
        Method::GET,
        "/api/v1/plugins/health/exercise/weeks/2026-06-10",
        None,
        Value::Null,
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(week["week_start"], "2026-06-08");
    assert_eq!(week["week_end"], "2026-06-14");
    assert!(week["sessions"].as_array().unwrap().is_empty());
}

#[tokio::test]
async fn health_exercise_session_crud_works_under_api_v1() {
    let app = build_router(AppState::new(test_pool().await));
    let (enable_status, _) = request_json(
        app.clone(),
        Method::PATCH,
        "/api/v1/plugins/health",
        None,
        json!({"enabled": true}),
    )
    .await;
    assert_eq!(enable_status, StatusCode::OK);

    let (create_status, session) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/plugins/health/exercise/sessions",
        None,
        json!({
            "session_date": "2026-06-10",
            "session_type": "gym",
            "title": " Full body session ",
            "target_duration_minutes": 45,
            "details": {
                "gym": [{
                    "exercise_name": " Back squat ",
                    "sets": 3,
                    "reps": 5,
                    "weight": 80,
                    "weight_unit": " kg "
                }],
                "cardio": [{
                    "activity_type": "Indoor rowing",
                    "duration_minutes": 10,
                    "intensity": "Zone 2"
                }],
                "flexibility": [{
                    "movement_name": "Hip flexor stretch",
                    "sets": 2,
                    "hold_seconds": 45,
                    "side": "each"
                }]
            }
        }),
    )
    .await;
    assert_eq!(create_status, StatusCode::CREATED);
    assert_eq!(session["title"], "Full body session");
    assert_eq!(session["details"]["gym"][0]["exercise_name"], "Back squat");
    let session_id = session["id"].as_str().expect("session id");

    let (get_status, fetched) = request_json(
        app.clone(),
        Method::GET,
        &format!("/api/v1/plugins/health/exercise/sessions/{session_id}"),
        None,
        Value::Null,
    )
    .await;
    assert_eq!(get_status, StatusCode::OK);
    assert_eq!(
        fetched["details"]["cardio"][0]["activity_type"],
        "Indoor rowing"
    );

    let (update_status, updated) = request_json(
        app.clone(),
        Method::PUT,
        &format!("/api/v1/plugins/health/exercise/sessions/{session_id}"),
        None,
        json!({
            "session_date": "2026-06-11",
            "session_type": "cardio",
            "title": "Zone 2 row",
            "target_duration_minutes": 20,
            "status": "planned",
            "details": {
                "cardio": [{
                    "activity_type": "Indoor rowing",
                    "duration_minutes": 20,
                    "intensity": "Zone 2"
                }]
            }
        }),
    )
    .await;
    assert_eq!(update_status, StatusCode::OK);
    assert_eq!(updated["session_type"], "cardio");
    assert!(updated["details"]["gym"].as_array().unwrap().is_empty());
    assert_eq!(updated["details"]["cardio"][0]["duration_minutes"], 20);

    let (status_update_status, done) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/plugins/health/exercise/sessions/{session_id}/status"),
        None,
        json!({"status": "done"}),
    )
    .await;
    assert_eq!(status_update_status, StatusCode::OK);
    assert_eq!(done["status"], "done");

    let (delete_status, delete_body) = request_json(
        app.clone(),
        Method::DELETE,
        &format!("/api/v1/plugins/health/exercise/sessions/{session_id}"),
        None,
        Value::Null,
    )
    .await;
    assert_eq!(delete_status, StatusCode::NO_CONTENT);
    assert_eq!(delete_body, Value::Null);

    let (missing_status, _) = request_json(
        app,
        Method::GET,
        &format!("/api/v1/plugins/health/exercise/sessions/{session_id}"),
        None,
        Value::Null,
    )
    .await;
    assert_eq!(missing_status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn health_exercise_routes_require_auth_when_token_configured() {
    let app = build_router(AppState::new(test_pool().await).with_api_token("secret-token"));

    let (missing_status, missing_body) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/plugins/health/exercise/weeks/2026-06-10",
        None,
        Value::Null,
    )
    .await;
    assert_eq!(missing_status, StatusCode::UNAUTHORIZED);
    assert_eq!(missing_body["detail"], "missing or invalid API token");

    let (ok_status, week) = request_json(
        app,
        Method::GET,
        "/api/v1/plugins/health/exercise/weeks/2026-06-10",
        Some("secret-token"),
        Value::Null,
    )
    .await;
    assert_eq!(ok_status, StatusCode::OK);
    assert_eq!(week["week_start"], "2026-06-08");
}
