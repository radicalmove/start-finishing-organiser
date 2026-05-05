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
async fn bootstrap_endpoint_returns_home_summary_contract() {
    let app = test_app().await;
    let (project_status, project) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        json!({
            "title": "Weekly Project",
            "category": "work",
            "active_this_week": true
        }),
    )
    .await;
    assert_eq!(project_status, StatusCode::CREATED);

    let (task_status, _task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/tasks",
        json!({
            "verb_noun": "Today task",
            "project_id": project["id"],
            "when_bucket": "today",
            "block_type": "focus"
        }),
    )
    .await;
    assert_eq!(task_status, StatusCode::CREATED);

    let (inbox_status, _inbox) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Inbox item"}),
    )
    .await;
    assert_eq!(inbox_status, StatusCode::CREATED);

    let (current_status, _current) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/blocks",
        json!({
            "title": "Current",
            "date": "2026-05-06",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "block_type": "focus",
            "project_id": project["id"]
        }),
    )
    .await;
    assert_eq!(current_status, StatusCode::CREATED);

    let (next_status, _next) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/blocks",
        json!({
            "title": "Next",
            "date": "2026-05-06",
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "block_type": "admin"
        }),
    )
    .await;
    assert_eq!(next_status, StatusCode::CREATED);

    let (status, body) = request_json(
        app,
        Method::GET,
        "/api/v1/bootstrap?date=2026-05-06&time=09:30:00",
        Value::Null,
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["today"], "2026-05-06");
    assert_eq!(body["current_time"], "09:30:00");
    assert_eq!(body["weekly_projects"].as_array().unwrap().len(), 1);
    assert_eq!(body["inbox"]["unprocessed"], 1);
    assert_eq!(body["today_tasks"].as_array().unwrap().len(), 1);
    assert_eq!(body["today_blocks"].as_array().unwrap().len(), 2);
    assert_eq!(body["current_block"]["title"], "Current");
    assert_eq!(body["next_block"]["title"], "Next");
    assert_eq!(body["system"]["database_status"], "ok");
    assert!(body["system"]["import_supported_tables"]
        .as_array()
        .unwrap()
        .iter()
        .any(|table| table == "blocks"));
}
