use axum::body::Body;
use axum::http::{header, HeaderMap, Method, Request, StatusCode};
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

async fn request_status(
    app: axum::Router,
    method: Method,
    uri: &str,
    token: Option<&str>,
) -> StatusCode {
    let mut builder = Request::builder().method(method).uri(uri);
    if let Some(token) = token {
        builder = builder.header(header::AUTHORIZATION, format!("Bearer {token}"));
    }

    app.oneshot(builder.body(Body::empty()).expect("request"))
        .await
        .expect("response")
        .status()
}

async fn request_status_with_sfo_header(
    app: axum::Router,
    method: Method,
    uri: &str,
    token: &str,
) -> StatusCode {
    app.oneshot(
        Request::builder()
            .method(method)
            .uri(uri)
            .header("x-sfo-api-token", token)
            .body(Body::empty())
            .expect("request"),
    )
    .await
    .expect("response")
    .status()
}

async fn cors_preflight_status(
    app: axum::Router,
    uri: &str,
    origin: &str,
    request_method: Method,
) -> (StatusCode, HeaderMap) {
    let response = app
        .oneshot(
            Request::builder()
                .method(Method::OPTIONS)
                .uri(uri)
                .header(header::ORIGIN, origin)
                .header(
                    header::ACCESS_CONTROL_REQUEST_METHOD,
                    request_method.as_str(),
                )
                .header(
                    header::ACCESS_CONTROL_REQUEST_HEADERS,
                    "authorization,content-type",
                )
                .body(Body::empty())
                .expect("request"),
        )
        .await
        .expect("response");

    (response.status(), response.headers().clone())
}

#[tokio::test]
async fn api_is_open_when_no_token_is_configured() {
    let app = build_router(AppState::new(test_pool().await));

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/projects",
        None,
        json!({"title": "Open dev project"}),
    )
    .await;

    assert_eq!(status, StatusCode::CREATED);
    assert_eq!(body["title"], "Open dev project");
}

#[tokio::test]
async fn api_requires_bearer_token_when_configured() {
    let app = build_router(AppState::new(test_pool().await).with_api_token("secret-token"));

    let (missing_status, missing_body) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        None,
        json!({"title": "Blocked project"}),
    )
    .await;
    assert_eq!(missing_status, StatusCode::UNAUTHORIZED);
    assert_eq!(missing_body["detail"], "missing or invalid API token");

    let (wrong_status, _) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/projects",
        Some("wrong-token"),
        json!({"title": "Blocked project"}),
    )
    .await;
    assert_eq!(wrong_status, StatusCode::UNAUTHORIZED);

    let (ok_status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/projects",
        Some("secret-token"),
        json!({"title": "Authorized project"}),
    )
    .await;
    assert_eq!(ok_status, StatusCode::CREATED);
    assert_eq!(body["title"], "Authorized project");
}

#[tokio::test]
async fn api_accepts_x_sfo_api_token_header() {
    let app = build_router(AppState::new(test_pool().await).with_api_token("secret-token"));

    let status =
        request_status_with_sfo_header(app, Method::GET, "/api/v1/bootstrap", "secret-token").await;
    assert_eq!(status, StatusCode::OK);
}

#[tokio::test]
async fn auth_runs_before_unknown_api_path_returns_404() {
    let app = build_router(AppState::new(test_pool().await).with_api_token("secret-token"));

    let missing_status = request_status(app.clone(), Method::GET, "/api/v1/unknown", None).await;
    assert_eq!(missing_status, StatusCode::UNAUTHORIZED);

    let authorized_status =
        request_status(app, Method::GET, "/api/v1/unknown", Some("secret-token")).await;
    assert_eq!(authorized_status, StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn healthz_and_auth_status_do_not_require_token() {
    let app = build_router(AppState::new(test_pool().await).with_api_token("secret-token"));

    let (health_status, health) =
        request_json(app.clone(), Method::GET, "/healthz", None, Value::Null).await;
    assert_eq!(health_status, StatusCode::OK);
    assert_eq!(health["status"], "ok");

    let (status_status, status) =
        request_json(app, Method::GET, "/api/v1/auth/status", None, Value::Null).await;
    assert_eq!(status_status, StatusCode::OK);
    assert_eq!(status["auth_required"], true);
}

#[tokio::test]
async fn cors_preflight_is_public_when_auth_is_configured() {
    let app = build_router(AppState::new(test_pool().await).with_api_token("secret-token"));

    let (status, headers) = cors_preflight_status(
        app.clone(),
        "/api/v1/bootstrap",
        "tauri://localhost",
        Method::GET,
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert!(headers.contains_key(header::ACCESS_CONTROL_ALLOW_ORIGIN));
    assert!(headers.contains_key(header::ACCESS_CONTROL_ALLOW_HEADERS));

    let (https_status, https_headers) = cors_preflight_status(
        app.clone(),
        "/api/v1/bootstrap",
        "https://tauri.localhost",
        Method::GET,
    )
    .await;

    assert_eq!(https_status, StatusCode::OK);
    assert!(https_headers.contains_key(header::ACCESS_CONTROL_ALLOW_ORIGIN));

    let (put_status, put_headers) =
        cors_preflight_status(app, "/api/v1/daily-focus", "tauri://localhost", Method::PUT).await;

    assert_eq!(put_status, StatusCode::OK);
    assert!(put_headers.contains_key(header::ACCESS_CONTROL_ALLOW_ORIGIN));
    assert!(put_headers
        .get(header::ACCESS_CONTROL_ALLOW_METHODS)
        .and_then(|value| value.to_str().ok())
        .is_some_and(|methods| methods.contains("PUT")));
}
