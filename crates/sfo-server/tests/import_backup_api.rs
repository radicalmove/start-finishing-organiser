use axum::body::Body;
use axum::http::{Method, Request, StatusCode};
use http_body_util::BodyExt;
use serde_json::{json, Value};
use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::{build_router, AppState};
use sqlx::sqlite::SqliteConnectOptions;
use std::str::FromStr;
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
async fn import_dry_run_endpoint_reports_source_counts() {
    let app = test_app().await;
    let path = temp_db_path("api-import");
    create_python_fixture(&path).await;

    let (status, body) = request_json(
        app,
        Method::POST,
        "/api/v1/import/python-sqlite/dry-run",
        json!({"source_path": path.to_string_lossy()}),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["source_sha256"].as_str().unwrap().len(), 64);
    assert_eq!(body["tables"][0]["table"], "projects");
    assert_eq!(body["tables"][0]["rows"], 1);

    let _ = std::fs::remove_file(path);
}

#[tokio::test]
async fn import_endpoint_backs_up_and_imports_source_data() {
    let app = test_app().await;
    let path = temp_db_path("api-import-real");
    let backup_dir = temp_dir_path("api-import-real-backups");
    create_python_fixture(&path).await;
    std::fs::create_dir_all(&backup_dir).expect("create backup dir");

    let (status, body) = request_json(
        app.clone(),
        Method::POST,
        "/api/v1/import/python-sqlite",
        json!({
            "source_path": path.to_string_lossy(),
            "backup_dir": backup_dir.to_string_lossy(),
        }),
    )
    .await;

    assert_eq!(status, StatusCode::OK);
    assert!(std::path::Path::new(body["backup_path"].as_str().unwrap()).exists());
    assert_eq!(body["tables"][0]["table"], "projects");
    assert_eq!(body["tables"][0]["imported_rows"], 1);

    let (project_status, projects) =
        request_json(app, Method::GET, "/api/v1/projects", Value::Null).await;
    assert_eq!(project_status, StatusCode::OK);
    assert_eq!(projects["total"], 1);
    assert_eq!(projects["items"][0]["title"], "A");

    let _ = std::fs::remove_file(path);
    let _ = std::fs::remove_dir_all(backup_dir);
}

#[tokio::test]
async fn backup_endpoint_reports_manifest() {
    let app = test_app().await;

    let (status, body) =
        request_json(app, Method::POST, "/api/v1/export/backup", Value::Null).await;

    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["database_status"], "ok");
    assert_eq!(body["schema"], "sfo-rust-foundation");
    assert!(body["tables"].as_array().unwrap().len() >= 3);
}

async fn create_python_fixture(path: &std::path::Path) {
    let url = format!("sqlite://{}", path.display());
    let options = SqliteConnectOptions::from_str(&url)
        .expect("sqlite options")
        .create_if_missing(true);
    let pool = sqlx::SqlitePool::connect_with(options)
        .await
        .expect("fixture connection");

    sqlx::query(
        r#"
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            size TEXT,
            time_horizon TEXT,
            target_date TEXT,
            level_of_success TEXT,
            why_link_text TEXT,
            active_this_week INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
        "#,
    )
    .execute(&pool)
    .await
    .expect("create projects");
    sqlx::query(
        r#"
        INSERT INTO projects (
            id, title, description, category, status, size, time_horizon,
            target_date, level_of_success, why_link_text, active_this_week,
            created_at, updated_at
        )
        VALUES (
            1, 'A', NULL, 'work', 'active', NULL, NULL,
            NULL, NULL, NULL, 0, '2026-01-02 03:04:05', NULL
        )
        "#,
    )
    .execute(&pool)
    .await
    .expect("insert project");

    sqlx::query(
        r#"
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            verb_noun TEXT NOT NULL,
            description TEXT,
            in_inbox INTEGER NOT NULL,
            archived_from_inbox INTEGER NOT NULL,
            intake_intent TEXT NOT NULL,
            intake_container TEXT NOT NULL,
            intake_processed_at TEXT,
            when_bucket TEXT NOT NULL,
            block_type TEXT,
            duration_minutes INTEGER,
            priority INTEGER,
            frog INTEGER NOT NULL,
            alignment TEXT,
            first_action TEXT,
            status TEXT NOT NULL,
            scheduled_for TEXT,
            owner_type TEXT NOT NULL,
            resurface_on TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL
        )
        "#,
    )
    .execute(&pool)
    .await
    .expect("create tasks");

    pool.close().await;
}

fn temp_db_path(label: &str) -> std::path::PathBuf {
    std::env::temp_dir().join(format!(
        "sfo-{label}-{}-{}.db",
        std::process::id(),
        chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
    ))
}

fn temp_dir_path(label: &str) -> std::path::PathBuf {
    std::env::temp_dir().join(format!(
        "sfo-{label}-{}-{}",
        std::process::id(),
        chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
    ))
}
