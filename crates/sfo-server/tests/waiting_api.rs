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
async fn waiting_items_can_be_created_listed_updated_and_resolved() {
    let app = test_app().await;
    let (project_status, project) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        json!({
            "title": "Waiting Project",
            "category": "work",
            "active_this_week": false
        }),
    )
    .await;
    assert_eq!(project_status, StatusCode::CREATED);

    let (create_status, waiting) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/waiting",
        json!({
            "description": "Waiting on Bob for draft",
            "person": "Bob",
            "project_id": project["id"],
            "last_followup": "2026-05-10"
        }),
    )
    .await;
    assert_eq!(create_status, StatusCode::CREATED);
    assert_eq!(waiting["description"], "Waiting on Bob for draft");
    assert_eq!(waiting["person"], "Bob");
    assert_eq!(waiting["project_id"], project["id"]);
    assert_eq!(waiting["last_followup"], "2026-05-10");

    let (list_status, list) =
        request_json(app.clone(), Method::GET, "/api/v1/waiting", Value::Null).await;
    assert_eq!(list_status, StatusCode::OK);
    assert_eq!(list["total"], 1);
    assert_eq!(list["items"][0]["id"], waiting["id"]);

    let waiting_id = waiting["id"].as_str().expect("waiting id");
    let (get_status, fetched) = request_json(
        app.clone(),
        Method::GET,
        &format!("/api/v1/waiting/{waiting_id}"),
        Value::Null,
    )
    .await;
    assert_eq!(get_status, StatusCode::OK);
    assert_eq!(fetched["id"], waiting["id"]);
    assert_eq!(fetched["description"], "Waiting on Bob for draft");
    assert_eq!(fetched["person"], "Bob");

    let (update_status, updated) = request_json(
        app.clone(),
        Method::PATCH,
        &format!("/api/v1/waiting/{waiting_id}"),
        json!({
            "person": "Alice",
            "last_followup": null
        }),
    )
    .await;
    assert_eq!(update_status, StatusCode::OK);
    assert_eq!(updated["person"], "Alice");
    assert!(updated["last_followup"].is_null());

    let (resolve_status, body) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/waiting/{waiting_id}/resolve"),
        Value::Null,
    )
    .await;
    assert_eq!(resolve_status, StatusCode::NO_CONTENT);
    assert!(body.is_null());

    let (list_status, list) = request_json(app, Method::GET, "/api/v1/waiting", Value::Null).await;
    assert_eq!(list_status, StatusCode::OK);
    assert_eq!(list["total"], 0);
}

#[tokio::test]
async fn guided_opp_capture_creates_waiting_item() {
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

    let (capture_status, body) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/capture/guided",
        json!({
            "capture_text": "Review Sam's budget",
            "item_kind": "task",
            "project_id": project["id"],
            "owner_type": "opp",
            "waiting_person": "Sam",
            "horizon": "week",
            "displacement_ack": true
        }),
    )
    .await;
    assert_eq!(capture_status, StatusCode::OK);
    assert_eq!(body["task"]["owner_type"], "opp");

    let (list_status, list) = request_json(app, Method::GET, "/api/v1/waiting", Value::Null).await;
    assert_eq!(list_status, StatusCode::OK);
    assert_eq!(list["total"], 1);
    assert_eq!(list["items"][0]["description"], "Review Sam's budget");
    assert_eq!(list["items"][0]["person"], "Sam");
    assert_eq!(list["items"][0]["project_id"], project["id"]);
}
