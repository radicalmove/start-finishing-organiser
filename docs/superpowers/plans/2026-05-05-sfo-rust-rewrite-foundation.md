# SFO Rust Rewrite Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the Rust workspace, shared domain crate, SQLite migration layer, Axum server shell, and baseline verification commands for the SFO rewrite.

**Architecture:** Keep the existing Python/Tauri app intact while adding a new Rust workspace at the repository root. The first Rust slice contains only foundational crates: `sfo-core` for shared types, `sfo-db` for SQLite setup and migrations, and `sfo-server` for HTTP state/routing with `/healthz`.

**Tech Stack:** Rust 2021, Cargo workspace, Axum 0.8, Tokio 1, SQLx 0.8 with SQLite, Serde, UUID, thiserror, tower-http, pytest for legacy baseline verification

---

## File Structure

- Create: `Cargo.toml`
- Modify: `.gitignore`
- Create: `crates/sfo-core/Cargo.toml`
- Create: `crates/sfo-core/src/lib.rs`
- Create: `crates/sfo-core/src/ids.rs`
- Create: `crates/sfo-db/Cargo.toml`
- Create: `crates/sfo-db/src/lib.rs`
- Create: `crates/sfo-db/src/config.rs`
- Create: `crates/sfo-db/src/error.rs`
- Create: `crates/sfo-db/migrations/0001_foundation.sql`
- Create: `crates/sfo-server/Cargo.toml`
- Create: `crates/sfo-server/src/lib.rs`
- Create: `crates/sfo-server/src/main.rs`
- Create: `crates/sfo-server/src/config.rs`
- Create: `crates/sfo-server/src/error.rs`
- Create: `crates/sfo-server/src/routes/mod.rs`
- Create: `crates/sfo-server/src/routes/health.rs`
- Create: `crates/sfo-server/src/state.rs`
- Create: `crates/sfo-server/tests/health.rs`
- Create: `docs/rust_rewrite.md`

## Baseline Commands

- Existing Python suite: `.venv/bin/python -m pytest`
- Existing Tauri shell: `cargo check --manifest-path src-tauri/Cargo.toml`
- New Rust workspace: `cargo test --workspace`

The existing Tauri shell currently requires ignored local bundle artifacts before `cargo check` succeeds:

- `src-tauri/resources/gmail_credentials.json`
- `src-tauri/bin/sfo-backend`

Do not commit those artifacts.

### Task 1: Add The Root Cargo Workspace

**Files:**
- Create: `Cargo.toml`
- Modify: `.gitignore`

- [ ] **Step 1: Add root `target/` ignore**

Modify `.gitignore` so the new root workspace build output is ignored:

```gitignore
# Rust build artifacts
target/
```

- [ ] **Step 2: Create the root workspace manifest**

Create `Cargo.toml`:

```toml
[workspace]
resolver = "2"
members = [
  "crates/sfo-core",
]
exclude = ["src-tauri"]

[workspace.package]
edition = "2021"
rust-version = "1.77.2"
license = ""
repository = ""

[workspace.dependencies]
anyhow = "1.0"
axum = "0.8"
http-body-util = "0.1"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
sqlx = { version = "0.8", features = ["runtime-tokio", "sqlite", "migrate", "uuid", "chrono"] }
thiserror = "2.0"
tokio = { version = "1", features = ["macros", "rt-multi-thread", "signal", "net"] }
tower = { version = "0.5", features = ["util"] }
tower-http = { version = "0.6", features = ["trace", "cors", "compression-full"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "fmt"] }
uuid = { version = "1", features = ["serde", "v4", "v7"] }
```

- [ ] **Step 3: Run the workspace test command to verify expected failure**

Run: `cargo test --workspace`

Expected: FAIL because `sfo-core` does not exist yet.

### Task 2: Create `sfo-core`

**Files:**
- Create: `crates/sfo-core/Cargo.toml`
- Create: `crates/sfo-core/src/lib.rs`
- Create: `crates/sfo-core/src/ids.rs`

- [ ] **Step 1: Create the crate manifest**

Create `crates/sfo-core/Cargo.toml`:

```toml
[package]
name = "sfo-core"
version = "0.1.0"
edition.workspace = true
rust-version.workspace = true
license.workspace = true
repository.workspace = true

[dependencies]
serde.workspace = true
thiserror.workspace = true
uuid.workspace = true

[dev-dependencies]
serde_json.workspace = true
```

- [ ] **Step 2: Write ID tests first**

Create `crates/sfo-core/src/ids.rs` with tests and placeholder implementation:

```rust
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct ProjectId(Uuid);

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct TaskId(Uuid);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_ids_serialize_as_uuid_strings() {
        let id = ProjectId::from_uuid(Uuid::nil());
        let json = serde_json::to_string(&id).expect("serialize project id");
        assert_eq!(json, "\"00000000-0000-0000-0000-000000000000\"");
    }

    #[test]
    fn task_ids_round_trip_through_json() {
        let original = TaskId::new();
        let json = serde_json::to_string(&original).expect("serialize task id");
        let decoded: TaskId = serde_json::from_str(&json).expect("deserialize task id");
        assert_eq!(decoded, original);
    }
}
```

- [ ] **Step 3: Export the module**

Create `crates/sfo-core/src/lib.rs`:

```rust
pub mod ids;

pub use ids::{ProjectId, TaskId};
```

- [ ] **Step 4: Run core tests to verify failure**

Run: `cargo test -p sfo-core`

Expected: FAIL because `ProjectId::from_uuid` and `TaskId::new` are not implemented.

- [ ] **Step 5: Implement the ID constructors**

Update `crates/sfo-core/src/ids.rs`:

```rust
use serde::{Deserialize, Serialize};
use uuid::Uuid;

macro_rules! id_type {
    ($name:ident) => {
        #[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Serialize, Deserialize)]
        #[serde(transparent)]
        pub struct $name(Uuid);

        impl $name {
            #[must_use]
            pub fn new() -> Self {
                Self(Uuid::now_v7())
            }

            #[must_use]
            pub const fn from_uuid(uuid: Uuid) -> Self {
                Self(uuid)
            }

            #[must_use]
            pub const fn as_uuid(self) -> Uuid {
                self.0
            }
        }

        impl Default for $name {
            fn default() -> Self {
                Self::new()
            }
        }
    };
}

id_type!(ProjectId);
id_type!(TaskId);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_ids_serialize_as_uuid_strings() {
        let id = ProjectId::from_uuid(Uuid::nil());
        let json = serde_json::to_string(&id).expect("serialize project id");
        assert_eq!(json, "\"00000000-0000-0000-0000-000000000000\"");
    }

    #[test]
    fn task_ids_round_trip_through_json() {
        let original = TaskId::new();
        let json = serde_json::to_string(&original).expect("serialize task id");
        let decoded: TaskId = serde_json::from_str(&json).expect("deserialize task id");
        assert_eq!(decoded, original);
    }
}
```

- [ ] **Step 6: Run core tests**

Run: `cargo test -p sfo-core`

Expected: PASS

### Task 3: Create `sfo-db`

**Files:**
- Modify: `Cargo.toml`
- Create: `crates/sfo-db/Cargo.toml`
- Create: `crates/sfo-db/src/lib.rs`
- Create: `crates/sfo-db/src/config.rs`
- Create: `crates/sfo-db/src/error.rs`
- Create: `crates/sfo-db/migrations/0001_foundation.sql`

- [ ] **Step 1: Add `sfo-db` to the workspace**

Modify root `Cargo.toml`:

```toml
members = [
  "crates/sfo-core",
  "crates/sfo-db",
]
exclude = ["src-tauri"]
```

- [ ] **Step 2: Create the crate manifest**

Create `crates/sfo-db/Cargo.toml`:

```toml
[package]
name = "sfo-db"
version = "0.1.0"
edition.workspace = true
rust-version.workspace = true
license.workspace = true
repository.workspace = true

[dependencies]
sqlx.workspace = true
thiserror.workspace = true
tracing.workspace = true

[dev-dependencies]
tokio.workspace = true
```

- [ ] **Step 3: Add a failing migration health test**

Create `crates/sfo-db/src/lib.rs`:

```rust
pub mod config;
pub mod error;

pub use config::DbConfig;
pub use error::DbError;

pub async fn connect(_config: &DbConfig) -> Result<sqlx::SqlitePool, DbError> {
    todo!("connect to sqlite")
}

pub async fn run_migrations(_pool: &sqlx::SqlitePool) -> Result<(), DbError> {
    todo!("run migrations")
}

pub async fn health_check(_pool: &sqlx::SqlitePool) -> Result<(), DbError> {
    todo!("check database health")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn migrations_create_app_metadata() {
        let config = DbConfig::new("sqlite::memory:");
        let pool = connect(&config).await.expect("connect");
        run_migrations(&pool).await.expect("migrate");

        let value: String = sqlx::query_scalar("SELECT value FROM app_metadata WHERE key = 'schema'")
            .fetch_one(&pool)
            .await
            .expect("schema metadata row");

        assert_eq!(value, "sfo-rust-foundation");
    }

    #[tokio::test]
    async fn health_check_runs_simple_query() {
        let config = DbConfig::new("sqlite::memory:");
        let pool = connect(&config).await.expect("connect");
        health_check(&pool).await.expect("healthy database");
    }
}
```

- [ ] **Step 4: Add config and error placeholders**

Create `crates/sfo-db/src/config.rs`:

```rust
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DbConfig {
    pub database_url: String,
}

impl DbConfig {
    #[must_use]
    pub fn new(database_url: impl Into<String>) -> Self {
        Self {
            database_url: database_url.into(),
        }
    }
}
```

Create `crates/sfo-db/src/error.rs`:

```rust
#[derive(Debug, thiserror::Error)]
pub enum DbError {
    #[error("sqlite error: {0}")]
    Sqlx(#[from] sqlx::Error),
    #[error("database migration error: {0}")]
    Migrate(#[from] sqlx::migrate::MigrateError),
}
```

- [ ] **Step 5: Run DB tests to verify failure**

Run: `cargo test -p sfo-db`

Expected: FAIL because DB functions still contain `todo!()`.

- [ ] **Step 6: Add the first SQLx migration**

Create `crates/sfo-db/migrations/0001_foundation.sql`:

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_metadata (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO app_metadata (key, value)
VALUES ('schema', 'sfo-rust-foundation')
ON CONFLICT(key) DO UPDATE SET
  value = excluded.value,
  updated_at = CURRENT_TIMESTAMP;
```

- [ ] **Step 7: Implement DB connection, migrations, and health**

Update `crates/sfo-db/src/lib.rs`:

```rust
pub mod config;
pub mod error;

use sqlx::sqlite::{SqliteConnectOptions, SqliteJournalMode, SqlitePoolOptions};
use std::str::FromStr;

pub use config::DbConfig;
pub use error::DbError;

pub async fn connect(config: &DbConfig) -> Result<sqlx::SqlitePool, DbError> {
    let is_memory = config.database_url.contains(":memory:");
    let mut options = SqliteConnectOptions::from_str(&config.database_url)?
        .create_if_missing(true)
        .foreign_keys(true);

    if !is_memory {
        options = options.journal_mode(SqliteJournalMode::Wal);
    }

    let pool = SqlitePoolOptions::new()
        .max_connections(if is_memory { 1 } else { 5 })
        .connect_with(options)
        .await?;

    sqlx::query("PRAGMA busy_timeout = 5000")
        .execute(&pool)
        .await?;

    Ok(pool)
}

pub async fn run_migrations(pool: &sqlx::SqlitePool) -> Result<(), DbError> {
    sqlx::migrate!("./migrations").run(pool).await?;
    Ok(())
}

pub async fn health_check(pool: &sqlx::SqlitePool) -> Result<(), DbError> {
    sqlx::query("SELECT 1").execute(pool).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn migrations_create_app_metadata() {
        let config = DbConfig::new("sqlite::memory:");
        let pool = connect(&config).await.expect("connect");
        run_migrations(&pool).await.expect("migrate");

        let value: String = sqlx::query_scalar("SELECT value FROM app_metadata WHERE key = 'schema'")
            .fetch_one(&pool)
            .await
            .expect("schema metadata row");

        assert_eq!(value, "sfo-rust-foundation");
    }

    #[tokio::test]
    async fn health_check_runs_simple_query() {
        let config = DbConfig::new("sqlite::memory:");
        let pool = connect(&config).await.expect("connect");
        health_check(&pool).await.expect("healthy database");
    }
}
```

- [ ] **Step 8: Run DB tests**

Run: `cargo test -p sfo-db`

Expected: PASS

### Task 4: Create `sfo-server`

**Files:**
- Modify: `Cargo.toml`
- Create: `crates/sfo-server/Cargo.toml`
- Create: `crates/sfo-server/src/lib.rs`
- Create: `crates/sfo-server/src/main.rs`
- Create: `crates/sfo-server/src/config.rs`
- Create: `crates/sfo-server/src/error.rs`
- Create: `crates/sfo-server/src/routes/mod.rs`
- Create: `crates/sfo-server/src/routes/health.rs`
- Create: `crates/sfo-server/src/state.rs`
- Create: `crates/sfo-server/tests/health.rs`

- [ ] **Step 1: Add `sfo-server` to the workspace**

Modify root `Cargo.toml`:

```toml
members = [
  "crates/sfo-core",
  "crates/sfo-db",
  "crates/sfo-server",
]
exclude = ["src-tauri"]
```

- [ ] **Step 2: Create the server manifest**

Create `crates/sfo-server/Cargo.toml`:

```toml
[package]
name = "sfo-server"
version = "0.1.0"
edition.workspace = true
rust-version.workspace = true
license.workspace = true
repository.workspace = true

[dependencies]
axum.workspace = true
serde.workspace = true
sfo-db = { path = "../sfo-db" }
sqlx.workspace = true
thiserror.workspace = true
tokio.workspace = true
tower-http.workspace = true
tracing.workspace = true
tracing-subscriber.workspace = true

[dev-dependencies]
http-body-util.workspace = true
serde_json.workspace = true
tower.workspace = true
```

- [ ] **Step 3: Write the failing health endpoint test**

Create `crates/sfo-server/tests/health.rs`:

```rust
use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::{build_router, AppState};
use tower::ServiceExt;

#[tokio::test]
async fn healthz_reports_ok_when_database_is_available() {
    let pool = connect(&DbConfig::new("sqlite::memory:"))
        .await
        .expect("connect test db");
    run_migrations(&pool).await.expect("migrate test db");

    let app = build_router(AppState::new(pool));
    let response = app
        .oneshot(
            Request::builder()
                .uri("/healthz")
                .body(Body::empty())
                .expect("request"),
        )
        .await
        .expect("response");

    assert_eq!(response.status(), StatusCode::OK);

    let body = response
        .into_body()
        .collect()
        .await
        .expect("collect body")
        .to_bytes();
    let json: serde_json::Value = serde_json::from_slice(&body).expect("json body");

    assert_eq!(json["status"], "ok");
    assert_eq!(json["database"], "ok");
}
```

- [ ] **Step 4: Add server modules with placeholders**

Create `crates/sfo-server/src/lib.rs`:

```rust
pub mod config;
pub mod error;
pub mod routes;
pub mod state;

pub use state::AppState;

pub fn build_router(_state: AppState) -> axum::Router {
    todo!("build axum router")
}
```

Create `crates/sfo-server/src/state.rs`:

```rust
#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::SqlitePool,
}

impl AppState {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }
}
```

Create `crates/sfo-server/src/config.rs`:

```rust
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ServerConfig {
    pub bind_addr: String,
    pub database_url: String,
}

impl ServerConfig {
    #[must_use]
    pub fn from_env() -> Self {
        Self {
            bind_addr: std::env::var("SFO_RUST_BIND")
                .unwrap_or_else(|_| "127.0.0.1:8088".to_string()),
            database_url: std::env::var("SFO_RUST_DATABASE_URL")
                .unwrap_or_else(|_| "sqlite://sfo-rust.db".to_string()),
        }
    }
}
```

Create `crates/sfo-server/src/error.rs`:

```rust
#[derive(Debug, thiserror::Error)]
pub enum ServerError {
    #[error(transparent)]
    Db(#[from] sfo_db::DbError),
    #[error("server io error: {0}")]
    Io(#[from] std::io::Error),
}
```

Create `crates/sfo-server/src/routes/mod.rs`:

```rust
pub mod health;
```

Create `crates/sfo-server/src/routes/health.rs`:

```rust
use axum::extract::State;
use axum::Json;
use serde::Serialize;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub database: &'static str,
}

pub async fn healthz(State(_state): State<AppState>) -> Json<HealthResponse> {
    todo!("return health response")
}
```

- [ ] **Step 5: Run server tests to verify failure**

Run: `cargo test -p sfo-server`

Expected: FAIL because `build_router` and `healthz` contain `todo!()`.

- [ ] **Step 6: Implement the router and health endpoint**

Update `crates/sfo-server/src/lib.rs`:

```rust
pub mod config;
pub mod error;
pub mod routes;
pub mod state;

use axum::{routing::get, Router};
use tower_http::trace::TraceLayer;

pub use state::AppState;

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/healthz", get(routes::health::healthz))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
```

Update `crates/sfo-server/src/routes/health.rs`:

```rust
use axum::extract::State;
use axum::Json;
use serde::Serialize;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub database: &'static str,
}

pub async fn healthz(State(state): State<AppState>) -> Json<HealthResponse> {
    let database = if sfo_db::health_check(&state.db).await.is_ok() {
        "ok"
    } else {
        "error"
    };

    Json(HealthResponse {
        status: if database == "ok" { "ok" } else { "degraded" },
        database,
    })
}
```

- [ ] **Step 7: Add the executable server entrypoint**

Create `crates/sfo-server/src/main.rs`:

```rust
use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::config::ServerConfig;
use sfo_server::{build_router, AppState};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| "sfo_server=info,tower_http=info".into());

    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .init();

    let config = ServerConfig::from_env();
    let db = connect(&DbConfig::new(config.database_url)).await?;
    run_migrations(&db).await?;

    let listener = tokio::net::TcpListener::bind(&config.bind_addr).await?;
    tracing::info!(bind_addr = %config.bind_addr, "starting SFO Rust server");

    axum::serve(listener, build_router(AppState::new(db))).await?;
    Ok(())
}
```

- [ ] **Step 8: Run server tests**

Run: `cargo test -p sfo-server`

Expected: PASS

### Task 5: Add Foundation Documentation

**Files:**
- Create: `docs/rust_rewrite.md`

- [ ] **Step 1: Document local commands**

Create `docs/rust_rewrite.md`:

```markdown
# SFO Rust Rewrite

The Rust rewrite lives beside the current Python app while feature parity is built incrementally.

## Current Slices

- `crates/sfo-core`: shared domain types.
- `crates/sfo-db`: SQLite connection and migrations.
- `crates/sfo-server`: Axum server shell.

## Local Verification

Run the existing Python suite:

```bash
.venv/bin/python -m pytest
```

Run the new Rust workspace:

```bash
cargo test --workspace
```

Run the Rust server locally:

```bash
SFO_RUST_DATABASE_URL=sqlite://sfo-rust.db cargo run -p sfo-server
curl http://127.0.0.1:8088/healthz
```

## Notes

The current `src-tauri` shell is still the existing Python-backed desktop wrapper. The Rust rewrite will replace that shell in a later milestone after the server and client API stabilize.
```

- [ ] **Step 2: Review documentation against the spec**

Run: `sed -n '1,220p' docs/rust_rewrite.md`

Expected: docs mention the current coexistence model and do not imply feature parity.

### Task 6: Verify The Foundation Slice

**Files:**
- Modify: `docs/superpowers/plans/2026-05-05-sfo-rust-rewrite-foundation.md`

- [ ] **Step 1: Run Rust formatting**

Run: `cargo fmt --all`

Expected: no formatting errors.

- [ ] **Step 2: Run Rust workspace tests**

Run: `cargo test --workspace`

Expected: PASS for `sfo-core`, `sfo-db`, and `sfo-server`.

- [ ] **Step 3: Run existing Python tests**

Run: `.venv/bin/python -m pytest`

Expected: PASS, currently `97 passed`.

- [ ] **Step 4: Check existing Tauri shell compile baseline**

Run: `cargo check --manifest-path src-tauri/Cargo.toml`

Expected: PASS if ignored local placeholders exist for `src-tauri/resources/gmail_credentials.json` and `src-tauri/bin/sfo-backend`.

- [ ] **Step 5: Verify diff scope**

Run: `git diff --stat`

Expected: only root Rust workspace files, `docs/rust_rewrite.md`, `.gitignore`, and the spec/plan docs changed.

- [ ] **Step 6: Commit the foundation plan/spec checkpoint before implementation or after the foundation slice if batching is preferred**

Run:

```bash
git add .gitignore Cargo.toml crates docs/rust_rewrite.md docs/superpowers/specs/2026-05-05-sfo-rust-rewrite-design.md docs/superpowers/plans/2026-05-05-sfo-rust-rewrite-foundation.md
git commit -m "feat: add rust rewrite foundation"
```

Expected: commit succeeds on branch `codex/rust-rewrite`.
