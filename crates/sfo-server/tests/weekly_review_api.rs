use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::{build_router, AppState};
use tower::ServiceExt;

async fn test_app() -> (axum::Router, sqlx::SqlitePool) {
    let pool = connect(&DbConfig::new("sqlite::memory:"))
        .await
        .expect("connect test db");
    run_migrations(&pool).await.expect("migrate test db");
    (build_router(AppState::new(pool.clone())), pool)
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
        .expect("body")
        .to_bytes();
    let json = if bytes.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&bytes).expect("json")
    };
    (status, json)
}

#[tokio::test]
async fn weekly_review_summary_returns_focus_resurface_and_cleanup() {
    let (app, _pool) = test_app().await;
    let (project_status, _project) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        json!({"title": "Weekly Project", "category": "work", "active_this_week": true}),
    )
    .await;
    assert_eq!(project_status, StatusCode::CREATED);

    let (status, body) = request_json(
        app,
        Method::GET,
        "/api/v1/weekly-review?date=2026-05-10",
        Value::Null,
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["review_date"], "2026-05-10");
    assert_eq!(body["week_starts_on"], "2026-05-04");
    assert_eq!(body["focus_counts"]["work"]["current"], 1);
    assert_eq!(body["focus_counts"]["work"]["cap"], 4);
}

#[tokio::test]
async fn weekly_review_move_to_week_updates_due_task() {
    let (app, pool) = test_app().await;
    let (task_status, task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/capture/guided",
        json!({
            "capture_text": "Due later",
            "item_kind": "task",
            "horizon": "month",
            "displacement_ack": true
        }),
    )
    .await;
    assert_eq!(task_status, StatusCode::OK);

    let task_id = task["task"]["id"].as_str().unwrap();
    sqlx::query("UPDATE tasks SET resurface_on = ? WHERE id = ?")
        .bind("2026-05-09")
        .bind(task_id)
        .execute(&pool)
        .await
        .expect("make task due");

    let (status, moved) = request_json(
        app,
        Method::POST,
        &format!("/api/v1/weekly-review/tasks/{task_id}/move-to-week"),
        Value::Null,
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(moved["id"], task_id);
    assert_eq!(moved["when_bucket"], "week");
    assert!(moved["resurface_on"].is_null());
}
