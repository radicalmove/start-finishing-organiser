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
async fn guided_capture_creates_task_under_api_v1() {
    let app = test_app().await;

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/capture/guided",
        json!({
            "capture_text": "Year task",
            "item_kind": "task",
            "horizon": "year",
            "displacement_ack": true
        }),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["task"]["verb_noun"], "Year task");
    assert_eq!(body["task"]["in_inbox"], false);
    assert_eq!(body["task"]["when_bucket"], "later");
    assert!(body["task"]["resurface_on"].is_string());
}

#[tokio::test]
async fn guided_capture_creates_project_under_api_v1() {
    let app = test_app().await;

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/capture/guided",
        json!({
            "capture_text": "Plan annual roadmap",
            "item_kind": "project",
            "horizon": "year",
            "include_this_week": false,
            "target_date": "2031-03-01",
            "displacement_ack": true
        }),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["project"]["title"], "Plan annual roadmap");
    assert_eq!(body["project"]["time_horizon"], "year");
    assert_eq!(body["project"]["active_this_week"], false);
}

#[tokio::test]
async fn guided_capture_requires_project_for_source_support_task() {
    let app = test_app().await;
    let (capture_status, source) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Inbox source"}),
    )
    .await;
    assert_eq!(capture_status, StatusCode::CREATED);

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/capture/guided",
        json!({
            "capture_text": "Action this",
            "source_task_id": source["id"],
            "inbox_intent": "support_project",
            "item_kind": "task",
            "displacement_ack": true
        }),
    )
    .await;

    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["detail"]
        .as_str()
        .expect("error detail")
        .contains("Select an existing project"));
}

#[tokio::test]
async fn guided_capture_processes_source_task_with_project_link() {
    let app = test_app().await;
    let (project_status, project) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        json!({
            "title": "Support Project",
            "category": "work",
            "active_this_week": false
        }),
    )
    .await;
    assert_eq!(project_status, StatusCode::CREATED);
    let (capture_status, source) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Inbox source", "description": "Original notes"}),
    )
    .await;
    assert_eq!(capture_status, StatusCode::CREATED);

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/capture/guided",
        json!({
            "capture_text": "Action this",
            "description": "Refined notes",
            "source_task_id": source["id"],
            "inbox_intent": "support_project",
            "item_kind": "task",
            "project_id": project["id"],
            "horizon": "month",
            "displacement_ack": true
        }),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["task"]["id"], source["id"]);
    assert_eq!(body["task"]["project_id"], project["id"]);
    assert_eq!(body["task"]["in_inbox"], false);
    assert_eq!(body["task"]["intake_intent"], "support_project");
    assert_eq!(body["task"]["when_bucket"], "month");
    assert!(body["task"]["resurface_on"].is_string());
}

#[tokio::test]
async fn guided_capture_routes_source_task_to_learning() {
    let app = test_app().await;
    let (capture_status, source) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Inbox source"}),
    )
    .await;
    assert_eq!(capture_status, StatusCode::CREATED);

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/capture/guided",
        json!({
            "capture_text": "Read this later",
            "source_task_id": source["id"],
            "inbox_intent": "learn_explore",
            "item_kind": "task"
        }),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["source_task"]["id"], source["id"]);
    assert_eq!(body["source_task"]["verb_noun"], "Read this later");
    assert_eq!(body["source_task"]["in_inbox"], false);
    assert_eq!(body["source_task"]["intake_container"], "learn_explore");
}
