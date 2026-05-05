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
async fn blocks_crud_works_under_api_v1() {
    let app = test_app().await;

    let (status, body) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/blocks",
        json!({
            "title": "Focus block",
            "date": "2026-05-06",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "block_type": "focus",
            "notes": "No meetings"
        }),
    )
    .await;

    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(body["title"], "Focus block");
    assert_eq!(body["date"], "2026-05-06");
    assert_eq!(body["block_type"], "focus");
    let block_id = body["id"].as_str().expect("block id");

    let (list_status, list_body) =
        request_json(app.clone(), Method::GET, "/api/v1/blocks", Value::Null).await;
    assert_eq!(list_status, StatusCode::OK);
    assert_eq!(list_body["total"], 1);

    let (update_status, update_body) = request_json(
        app.clone(),
        Method::PATCH,
        &format!("/api/v1/blocks/{block_id}"),
        json!({"title": "Renamed", "notes": null}),
    )
    .await;
    assert_eq!(update_status, StatusCode::OK);
    assert_eq!(update_body["title"], "Renamed");
    assert!(update_body["notes"].is_null());

    let (delete_status, delete_body) = request_json(
        app,
        Method::DELETE,
        &format!("/api/v1/blocks/{block_id}"),
        Value::Null,
    )
    .await;
    assert_eq!(delete_status, StatusCode::NO_CONTENT);
    assert_eq!(delete_body, Value::Null);
}
