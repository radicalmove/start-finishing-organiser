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
async fn inbox_route_undo_and_containers_work_under_api_v1() {
    let app = test_app().await;
    let (capture_status, task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Read rust notes"}),
    )
    .await;
    assert_eq!(capture_status, StatusCode::CREATED);
    let task_id = task["id"].as_str().expect("task id");

    let (initial_containers_status, initial_containers) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/inbox/containers",
        Value::Null,
    )
    .await;
    assert_eq!(initial_containers_status, StatusCode::OK);
    assert_eq!(initial_containers["counts"]["unprocessed"], 1);
    assert_eq!(initial_containers["unprocessed"][0]["id"], task_id);

    let (route_status, routed) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/inbox/{task_id}/route"),
        json!({"intent": "learn_explore"}),
    )
    .await;
    assert_eq!(route_status, StatusCode::OK);
    assert_eq!(routed["in_inbox"], false);
    assert_eq!(routed["intake_container"], "learn_explore");

    let (containers_status, containers) = request_json(
        app.clone(),
        Method::GET,
        "/api/v1/inbox/containers",
        Value::Null,
    )
    .await;
    assert_eq!(containers_status, StatusCode::OK);
    assert_eq!(containers["counts"]["unprocessed"], 0);
    assert!(containers["unprocessed"].as_array().unwrap().is_empty());
    assert_eq!(containers["counts"]["learn_explore"], 1);
    assert_eq!(containers["learning"][0]["id"], task_id);

    let (undo_status, undone) = request_json(
        app,
        Method::POST,
        &format!("/api/v1/inbox/{task_id}/undo"),
        Value::Null,
    )
    .await;
    assert_eq!(undo_status, StatusCode::OK);
    assert_eq!(undone["in_inbox"], true);
    assert_eq!(undone["intake_container"], "unprocessed");
}

#[tokio::test]
async fn inbox_recycle_and_restore_work_under_api_v1() {
    let app = test_app().await;
    let (capture_status, task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Remove this"}),
    )
    .await;
    assert_eq!(capture_status, StatusCode::CREATED);
    let task_id = task["id"].as_str().expect("task id");

    let (recycle_status, recycled) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/inbox/{task_id}/recycle"),
        Value::Null,
    )
    .await;
    assert_eq!(recycle_status, StatusCode::OK);
    assert_eq!(recycled["status"], "archived");
    assert_eq!(recycled["archived_from_inbox"], true);

    let (restore_status, restored) = request_json(
        app,
        Method::POST,
        &format!("/api/v1/inbox/{task_id}/restore"),
        Value::Null,
    )
    .await;
    assert_eq!(restore_status, StatusCode::OK);
    assert_eq!(restored["in_inbox"], true);
    assert_eq!(restored["status"], "pending");
}

#[tokio::test]
async fn inbox_park_until_keeps_future_items_visible_and_returns_due_items_under_api_v1() {
    let app = test_app().await;
    let (future_status, future_task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Renew passport"}),
    )
    .await;
    assert_eq!(future_status, StatusCode::CREATED);
    let future_task_id = future_task["id"].as_str().expect("future task id");

    let (due_status, due_task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Print calendar"}),
    )
    .await;
    assert_eq!(due_status, StatusCode::CREATED);
    let due_task_id = due_task["id"].as_str().expect("due task id");

    let (future_route_status, future_routed) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/inbox/{future_task_id}/route"),
        json!({"intent": "park_let_go", "parked_until": "2099-01-01T09:00:00Z"}),
    )
    .await;
    assert_eq!(future_route_status, StatusCode::OK);
    assert_eq!(future_routed["in_inbox"], false);
    assert_eq!(future_routed["intake_container"], "park_let_go");
    assert_eq!(future_routed["parked_until"], "2099-01-01T09:00:00Z");

    let (due_route_status, due_routed) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/inbox/{due_task_id}/route"),
        json!({"intent": "park_let_go", "parked_until": "2026-01-01T09:00:00Z"}),
    )
    .await;
    assert_eq!(due_route_status, StatusCode::OK);
    assert_eq!(due_routed["in_inbox"], false);

    let (containers_status, containers) =
        request_json(app, Method::GET, "/api/v1/inbox/containers", Value::Null).await;
    assert_eq!(containers_status, StatusCode::OK);
    assert_eq!(containers["counts"]["unprocessed"], 1);
    assert_eq!(containers["counts"]["park_let_go"], 1);
    assert_eq!(containers["unprocessed"][0]["id"], due_task_id);
    assert_eq!(containers["unprocessed"][0]["parked_until"], Value::Null);
    assert_eq!(containers["parked"][0]["id"], future_task_id);
    assert_eq!(
        containers["parked"][0]["parked_until"],
        "2099-01-01T09:00:00Z"
    );
}
