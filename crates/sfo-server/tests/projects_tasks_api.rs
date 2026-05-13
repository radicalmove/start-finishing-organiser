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

async fn get_json(app: axum::Router, uri: &str) -> (StatusCode, Value) {
    request_json(app, Method::GET, uri, Value::Null).await
}

#[tokio::test]
async fn projects_crud_and_pagination_work_under_api_v1() {
    let app = test_app().await;

    let (status, project) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        json!({
            "title": "Test Project",
            "description": "Scope",
            "category": "work",
            "active_this_week": false
        }),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(project["title"], "Test Project");

    let (status, page) = get_json(app.clone(), "/api/v1/projects?page=1&page_size=2").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(page["total"], 1);
    assert_eq!(page["items"][0]["id"], project["id"]);

    let (status, updated) = request_json(
        app.clone(),
        Method::PATCH,
        &format!("/api/v1/projects/{}", project["id"].as_str().unwrap()),
        json!({"title": "Updated Project"}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["title"], "Updated Project");

    let (status, _) = request_json(
        app,
        Method::DELETE,
        &format!("/api/v1/projects/{}", project["id"].as_str().unwrap()),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn project_weekly_cap_returns_bad_request() {
    let app = test_app().await;

    for index in 0..4 {
        let (status, _) = request_json(
            app.clone(),
            Method::POST,
            "/api/v1/projects",
            json!({
                "title": format!("Work {index}"),
                "category": "work",
                "active_this_week": true
            }),
        )
        .await;
        assert_eq!(status, StatusCode::CREATED);
    }

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/projects",
        json!({
            "title": "Overflow",
            "category": "work",
            "active_this_week": true
        }),
    )
    .await;

    assert_eq!(status, StatusCode::BAD_REQUEST);
    assert!(body["detail"].as_str().unwrap().contains("Weekly cap"));
}

#[tokio::test]
async fn project_card_endpoints_save_shape_and_create_chunks() {
    let app = test_app().await;
    let (status, project) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        json!({
            "title": "Plan roadmap",
            "category": "work",
            "active_this_week": false
        }),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    let project_id = project["id"].as_str().unwrap();

    let (status, card) = request_json(
        app.clone(),
        Method::PUT,
        &format!("/api/v1/projects/{project_id}/card"),
        json!({
            "title": "Plan annual roadmap",
            "description": "Shape it clearly",
            "category": "personal",
            "status": "active",
            "time_horizon": "quarter",
            "start_date": "2026-05-15",
            "target_date": "2026-08-01",
            "level_of_success": "epic",
            "why_link_text": "Calmer month",
            "drag_points_notes": "Too many commitments",
            "gates_notes": "Use planning strengths",
            "budget_notes": "Two focus blocks",
            "active_this_week": false,
            "success_pack": {
                "guides": "Charlie",
                "peers": "",
                "supporters": "Morgan",
                "beneficiaries": "Family"
            }
        }),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(card["project"]["title"], "Plan annual roadmap");
    assert_eq!(card["project"]["start_date"], "2026-05-15");
    assert_eq!(card["success_pack"]["guides"], "Charlie");
    assert!(card["success_pack"]["peers"].is_null());

    let (status, chunk) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/projects/{project_id}/chunks"),
        json!({
            "verb_noun": "Draft first roadmap",
            "description": "Starter chunk",
            "duration_minutes": 45,
            "frog": true
        }),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(chunk["project_id"], project_id);
    assert_eq!(chunk["when_bucket"], "week");

    let (status, card) = request_json(
        app,
        Method::GET,
        &format!("/api/v1/projects/{project_id}/card"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(card["chunks"].as_array().unwrap().len(), 1);
    assert_eq!(card["chunks"][0]["verb_noun"], "Draft first roadmap");
}

#[tokio::test]
async fn tasks_crud_and_lifecycle_work_under_api_v1() {
    let app = test_app().await;

    let (status, task) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/tasks",
        json!({
            "verb_noun": "Draft test plan",
            "when_bucket": "today"
        }),
    )
    .await;
    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(task["verb_noun"], "Draft test plan");

    let task_id = task["id"].as_str().unwrap();
    let (status, updated) = request_json(
        app.clone(),
        Method::PATCH,
        &format!("/api/v1/tasks/{task_id}"),
        json!({"frog": true}),
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(updated["frog"], true);

    let (status, completed) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/tasks/{task_id}/complete"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(completed["status"], "done");
    assert!(completed["completed_at"].is_string());

    let (status, reopened) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/tasks/{task_id}/reopen"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(reopened["status"], "pending");
    assert!(reopened["completed_at"].is_null());

    let (status, archived) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/tasks/{task_id}/archive"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(archived["status"], "archived");

    let (status, restored) = request_json(
        app.clone(),
        Method::POST,
        &format!("/api/v1/tasks/{task_id}/restore"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(restored["status"], "pending");

    let (status, page) = get_json(app.clone(), "/api/v1/tasks?page=1&page_size=2").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(page["total"], 1);

    let (status, _) = request_json(
        app,
        Method::DELETE,
        &format!("/api/v1/tasks/{task_id}"),
        Value::Null,
    )
    .await;
    assert_eq!(status, StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn quick_capture_creates_unprocessed_inbox_task() {
    let app = test_app().await;

    let (status, task) = request_json(
        app,
        Method::POST,
        "/api/v1/inbox/quick-capture",
        json!({"verb_noun": "Remember this"}),
    )
    .await;

    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(task["verb_noun"], "Remember this");
    assert_eq!(task["in_inbox"], true);
    assert_eq!(task["when_bucket"], "later");
    assert_eq!(task["intake_intent"], "unprocessed");
}
