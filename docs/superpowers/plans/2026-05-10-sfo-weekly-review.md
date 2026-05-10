# SFO Weekly Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Rust weekly review workflow: focus counts/toggles, due resurfacing, move-to-week, and completed-task cleanup.

**Architecture:** Add a small weekly-review vertical slice through the existing Rust crate layers, then expose it in the static Tauri launcher as a fifth `Review` workflow. Keep review state derived from existing project/task data; do not add migrations or persisted review notes in this slice.

**Tech Stack:** Rust, Axum, SQLx, SQLite, Node test runner, vanilla JavaScript, Tauri static web assets.

---

## File Structure

- Create: `crates/sfo-core/src/weekly_review.rs`
  - Defines `WeeklyReviewSummary`, `WeeklyFocusCounts`, `WeeklyFocusCount`, and `WeeklyReviewTask`.
- Modify: `crates/sfo-core/src/lib.rs`
  - Exports the new weekly-review DTO module.
- Create: `crates/sfo-db/src/weekly_review.rs`
  - Contains query functions for weekly projects, focus candidates, due resurface tasks, completed tasks, and move-to-week.
- Modify: `crates/sfo-db/src/lib.rs`
  - Exports the new repository module.
- Create: `crates/sfo-services/src/weekly_review.rs`
  - Adds `WeeklyReviewService` with summary and move-to-week use cases.
- Modify: `crates/sfo-services/src/lib.rs`
  - Exports `WeeklyReviewService`.
- Modify: `crates/sfo-server/src/routes/api.rs`
  - Adds `/weekly-review` routes and handlers.
- Create: `crates/sfo-server/tests/weekly_review_api.rs`
  - Covers summary and move-to-week HTTP contracts.
- Modify: `src-tauri/launcher/client.js`
  - Adds `review` workflow metadata, weekly-review request helpers, and review view-model mapping.
- Modify: `src-tauri/launcher/client.test.mjs`
  - Covers workflow metadata and review view-model behavior.
- Modify: `src-tauri/launcher/index.html`
  - Adds Review nav tab and workflow panel.
- Modify: `src-tauri/launcher/launcher.js`
  - Loads weekly review data, renders Review, wires focus toggle, move-to-week, archive, and refresh actions.
- Modify: `src-tauri/launcher/workflow-shell.test.mjs`
  - Updates workflow shell tests from four workflows to five.
- Modify: `src-tauri/launcher/mobile-shell.test.mjs`
  - Adds/updates mobile assertions for five-tab Review layout.
- Modify: `src-tauri/launcher/launcher.css`
  - Adds Review workflow layout using existing aesthetic tokens.
- Modify: `docs/rust_rewrite_parity_review.md`
  - Records weekly review slice progress after implementation.
- Modify: `docs/workflow_shell_ux_review.md`
  - Updates recommended next slice after implementation and review.

---

### Task 1: Core Weekly Review DTOs

**Files:**
- Create: `crates/sfo-core/src/weekly_review.rs`
- Modify: `crates/sfo-core/src/lib.rs`

- [ ] **Step 1: Write the failing DTO tests**

Add tests in `crates/sfo-core/src/weekly_review.rs`:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use crate::{ProjectCategory, TaskId, WhenBucket};
    use chrono::NaiveDate;

    #[test]
    fn weekly_review_summary_serializes_counts_and_rows() {
        let task_id = TaskId::new();
        let summary = WeeklyReviewSummary {
            review_date: NaiveDate::from_ymd_opt(2026, 5, 10).unwrap(),
            week_starts_on: NaiveDate::from_ymd_opt(2026, 5, 4).unwrap(),
            focus_counts: WeeklyFocusCounts {
                work: WeeklyFocusCount {
                    category: ProjectCategory::Work,
                    current: 3,
                    cap: 4,
                },
                personal: WeeklyFocusCount {
                    category: ProjectCategory::Personal,
                    current: 2,
                    cap: 3,
                },
            },
            weekly_projects: vec![],
            available_projects: vec![],
            resurface_due: vec![WeeklyReviewTask {
                id: task_id,
                title: "Write outline".to_string(),
                description: None,
                when_bucket: WhenBucket::Month,
                status: "pending".to_string(),
                project_id: None,
                project_title: None,
                resurface_on: Some(NaiveDate::from_ymd_opt(2026, 5, 10).unwrap()),
                completed_at: None,
            }],
            completed_tasks: vec![],
        };

        let json = serde_json::to_value(summary).expect("serialize weekly review");

        assert_eq!(json["review_date"], "2026-05-10");
        assert_eq!(json["week_starts_on"], "2026-05-04");
        assert_eq!(json["focus_counts"]["work"]["current"], 3);
        assert_eq!(json["focus_counts"]["personal"]["cap"], 3);
        assert_eq!(json["resurface_due"][0]["id"], task_id.to_string());
        assert_eq!(json["resurface_due"][0]["when_bucket"], "month");
    }
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cargo test -p sfo-core weekly_review`

Expected: FAIL because `weekly_review` module and DTOs do not exist.

- [ ] **Step 3: Add minimal DTO implementation**

Create `crates/sfo-core/src/weekly_review.rs`:

```rust
use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};

use crate::{Project, ProjectCategory, ProjectId, TaskId, WhenBucket};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyReviewSummary {
    pub review_date: NaiveDate,
    pub week_starts_on: NaiveDate,
    pub focus_counts: WeeklyFocusCounts,
    pub weekly_projects: Vec<Project>,
    pub available_projects: Vec<Project>,
    pub resurface_due: Vec<WeeklyReviewTask>,
    pub completed_tasks: Vec<WeeklyReviewTask>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyFocusCounts {
    pub work: WeeklyFocusCount,
    pub personal: WeeklyFocusCount,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyFocusCount {
    pub category: ProjectCategory,
    pub current: i64,
    pub cap: i64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WeeklyReviewTask {
    pub id: TaskId,
    pub title: String,
    pub description: Option<String>,
    pub when_bucket: WhenBucket,
    pub status: String,
    pub project_id: Option<ProjectId>,
    pub project_title: Option<String>,
    pub resurface_on: Option<NaiveDate>,
    pub completed_at: Option<DateTime<Utc>>,
}
```

Update `crates/sfo-core/src/lib.rs`:

```rust
pub mod weekly_review;
pub use weekly_review::*;
```

- [ ] **Step 4: Run the focused test**

Run: `cargo test -p sfo-core weekly_review`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sfo-core/src/lib.rs crates/sfo-core/src/weekly_review.rs
git commit -m "add weekly review core contracts"
```

---

### Task 2: Weekly Review Repository Queries

**Files:**
- Create: `crates/sfo-db/src/weekly_review.rs`
- Modify: `crates/sfo-db/src/lib.rs`

- [ ] **Step 1: Write failing repository tests**

Create tests in `crates/sfo-db/src/weekly_review.rs` after the query functions section:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{NaiveDate, Utc};
    use sfo_core::{ProjectCategory, ProjectCreate, TaskCreate, TaskStatus, WhenBucket};

    async fn test_pool() -> sqlx::SqlitePool {
        let pool = crate::connect(&crate::DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        crate::run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn weekly_summary_queries_return_focus_resurface_and_completed_rows() {
        let pool = test_pool().await;
        let active_project = crate::planning::create_project(&pool, ProjectCreate {
            title: "Weekly work".to_string(),
            description: None,
            category: ProjectCategory::Work,
            size: None,
            time_horizon: Some("week".to_string()),
            target_date: None,
            level_of_success: None,
            why_link_text: None,
            active_this_week: true,
        })
        .await
        .expect("project");

        let due_task = crate::planning::create_task(&pool, TaskCreate {
            verb_noun: "Resurface due item".to_string(),
            project_id: Some(active_project.id),
            description: None,
            in_inbox: false,
            when_bucket: WhenBucket::Month,
            block_type: None,
            duration_minutes: None,
            priority: None,
            frog: false,
            alignment: None,
            first_action: None,
            scheduled_for: None,
            owner_type: Default::default(),
        })
        .await
        .expect("due task");

        sqlx::query("UPDATE tasks SET resurface_on = ? WHERE id = ?")
            .bind("2026-05-09")
            .bind(due_task.id.to_string())
            .execute(&pool)
            .await
            .expect("set resurface");

        let completed_task = crate::planning::create_task(&pool, TaskCreate {
            verb_noun: "Completed this week".to_string(),
            project_id: None,
            description: None,
            in_inbox: false,
            when_bucket: WhenBucket::Week,
            block_type: None,
            duration_minutes: None,
            priority: None,
            frog: false,
            alignment: None,
            first_action: None,
            scheduled_for: None,
            owner_type: Default::default(),
        })
        .await
        .expect("completed task");

        sqlx::query("UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?")
            .bind(TaskStatus::Done.as_str())
            .bind(Utc::now().to_rfc3339())
            .bind(completed_task.id.to_string())
            .execute(&pool)
            .await
            .expect("complete task");

        assert_eq!(focus_count(&pool, ProjectCategory::Work).await.unwrap(), 1);
        assert_eq!(weekly_projects(&pool).await.unwrap().len(), 1);
        assert_eq!(available_projects(&pool).await.unwrap().len(), 1);
        assert_eq!(
            due_resurface_tasks(&pool, NaiveDate::from_ymd_opt(2026, 5, 10).unwrap())
                .await
                .unwrap()[0]
                .id,
            due_task.id
        );
        assert_eq!(
            completed_tasks_since(&pool, NaiveDate::from_ymd_opt(2026, 5, 4).unwrap())
                .await
                .unwrap()[0]
                .id,
            completed_task.id
        );
    }

    #[tokio::test]
    async fn move_task_to_week_sets_week_bucket_and_clears_resurface() {
        let pool = test_pool().await;
        let task = crate::planning::create_task(&pool, TaskCreate {
            verb_noun: "Move me".to_string(),
            project_id: None,
            description: None,
            in_inbox: false,
            when_bucket: WhenBucket::Quarter,
            block_type: None,
            duration_minutes: None,
            priority: None,
            frog: true,
            alignment: None,
            first_action: Some("Start".to_string()),
            scheduled_for: None,
            owner_type: Default::default(),
        })
        .await
        .expect("task");

        sqlx::query("UPDATE tasks SET resurface_on = ? WHERE id = ?")
            .bind("2026-05-09")
            .bind(task.id.to_string())
            .execute(&pool)
            .await
            .expect("set resurface");

        let moved = move_task_to_week(&pool, task.id).await.unwrap().unwrap();

        assert_eq!(moved.when_bucket, WhenBucket::Week);
        assert!(moved.resurface_on.is_none());
        assert!(moved.frog);
        assert_eq!(moved.first_action.as_deref(), Some("Start"));
    }
}
```

- [ ] **Step 2: Run the repository tests to verify failure**

Run: `cargo test -p sfo-db weekly_review`

Expected: FAIL because `weekly_review` module and functions do not exist.

- [ ] **Step 3: Add repository implementation**

Create `crates/sfo-db/src/weekly_review.rs`.

Implementation notes:

- Reuse `crate::planning::{ProjectRow, TaskRow}` inside the crate.
- Return `Vec<Project>` and `Vec<Task>` from repository functions.
- Use the same focus-count rule as `planning::count_active_projects_by_category`.
- Use `status = 'active'` for available projects so paused/completed projects are not offered as weekly focus candidates.
- Use `status NOT IN ('done', 'archived')` for due resurfacing.
- Use `status = 'done'` and `completed_at >= ?` for cleanup candidates.

Function signatures:

```rust
pub async fn focus_count(
    pool: &sqlx::SqlitePool,
    category: ProjectCategory,
) -> Result<i64, DbError>;

pub async fn weekly_projects(pool: &sqlx::SqlitePool) -> Result<Vec<Project>, DbError>;

pub async fn available_projects(pool: &sqlx::SqlitePool) -> Result<Vec<Project>, DbError>;

pub async fn due_resurface_tasks(
    pool: &sqlx::SqlitePool,
    review_date: NaiveDate,
) -> Result<Vec<Task>, DbError>;

pub async fn completed_tasks_since(
    pool: &sqlx::SqlitePool,
    week_starts_on: NaiveDate,
) -> Result<Vec<Task>, DbError>;

pub async fn move_task_to_week(
    pool: &sqlx::SqlitePool,
    id: TaskId,
) -> Result<Option<Task>, DbError>;
```

Update `crates/sfo-db/src/lib.rs`:

```rust
pub mod weekly_review;
```

- [ ] **Step 4: Run the repository tests**

Run: `cargo test -p sfo-db weekly_review`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sfo-db/src/lib.rs crates/sfo-db/src/weekly_review.rs
git commit -m "add weekly review database queries"
```

---

### Task 3: Weekly Review Service

**Files:**
- Create: `crates/sfo-services/src/weekly_review.rs`
- Modify: `crates/sfo-services/src/lib.rs`

- [ ] **Step 1: Write failing service tests**

Create `crates/sfo-services/src/weekly_review.rs` with tests first:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;
    use sfo_core::{TaskCreate, TaskStatus, WhenBucket};
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn service() -> WeeklyReviewService {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        WeeklyReviewService::new(pool)
    }

    #[tokio::test]
    async fn summary_uses_monday_week_start_and_focus_caps() {
        let service = service().await;
        let summary = service
            .summary(NaiveDate::from_ymd_opt(2026, 5, 10).unwrap())
            .await
            .expect("summary");

        assert_eq!(summary.week_starts_on, NaiveDate::from_ymd_opt(2026, 5, 4).unwrap());
        assert_eq!(summary.focus_counts.work.cap, 4);
        assert_eq!(summary.focus_counts.personal.cap, 3);
    }

    #[tokio::test]
    async fn move_to_week_rejects_done_tasks() {
        let service = service().await;
        let task = sfo_db::planning::create_task(&service.db, TaskCreate {
            verb_noun: "Already complete".to_string(),
            project_id: None,
            description: None,
            in_inbox: false,
            when_bucket: WhenBucket::Month,
            block_type: None,
            duration_minutes: None,
            priority: None,
            frog: false,
            alignment: None,
            first_action: None,
            scheduled_for: None,
            owner_type: Default::default(),
        })
        .await
        .expect("task");

        let done = sfo_db::planning::update_task(&service.db, &sfo_core::Task {
            status: TaskStatus::Done,
            ..task.clone()
        })
        .await
        .expect("done task");

        let error = service.move_task_to_week(done.id).await.expect_err("validation error");

        assert!(format!("{error}").contains("done or archived"));
    }
}
```

If struct update syntax is awkward because timestamps need preservation, set the task status with SQL in the test instead.

- [ ] **Step 2: Run the service tests to verify failure**

Run: `cargo test -p sfo-services weekly_review`

Expected: FAIL because `WeeklyReviewService` does not exist.

- [ ] **Step 3: Add service implementation**

Create `crates/sfo-services/src/weekly_review.rs`:

```rust
use chrono::{Datelike, Duration, NaiveDate};
use sfo_core::{
    ProjectCategory, Task, TaskId, TaskStatus, WeeklyFocusCount, WeeklyFocusCounts,
    WeeklyReviewSummary, WeeklyReviewTask,
};
use sfo_db::weekly_review as repo;

use crate::ServiceError;

#[derive(Clone)]
pub struct WeeklyReviewService {
    pub(crate) db: sqlx::SqlitePool,
}

impl WeeklyReviewService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn summary(&self, review_date: NaiveDate) -> Result<WeeklyReviewSummary, ServiceError> {
        let week_starts_on = week_start_monday(review_date);
        let work_count = repo::focus_count(&self.db, ProjectCategory::Work).await?;
        let personal_count = repo::focus_count(&self.db, ProjectCategory::Personal).await?;

        Ok(WeeklyReviewSummary {
            review_date,
            week_starts_on,
            focus_counts: WeeklyFocusCounts {
                work: WeeklyFocusCount {
                    category: ProjectCategory::Work,
                    current: work_count,
                    cap: ProjectCategory::Work.weekly_cap(),
                },
                personal: WeeklyFocusCount {
                    category: ProjectCategory::Personal,
                    current: personal_count,
                    cap: ProjectCategory::Personal.weekly_cap(),
                },
            },
            weekly_projects: repo::weekly_projects(&self.db).await?,
            available_projects: repo::available_projects(&self.db).await?,
            resurface_due: repo::due_resurface_tasks(&self.db, review_date)
                .await?
                .into_iter()
                .map(review_task)
                .collect(),
            completed_tasks: repo::completed_tasks_since(&self.db, week_starts_on)
                .await?
                .into_iter()
                .map(review_task)
                .collect(),
        })
    }

    pub async fn move_task_to_week(&self, id: TaskId) -> Result<WeeklyReviewTask, ServiceError> {
        let task = sfo_db::planning::get_task(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "task" })?;

        if matches!(task.status, TaskStatus::Done | TaskStatus::Archived) {
            return Err(ServiceError::Validation {
                field: "task",
                message: "done or archived tasks cannot be moved into week",
            });
        }

        let moved = repo::move_task_to_week(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "task" })?;

        Ok(review_task(moved))
    }
}

fn week_start_monday(date: NaiveDate) -> NaiveDate {
    date - Duration::days(i64::from(date.weekday().num_days_from_monday()))
}

fn review_task(task: Task) -> WeeklyReviewTask {
    WeeklyReviewTask {
        id: task.id,
        title: task.verb_noun,
        description: task.description,
        when_bucket: task.when_bucket,
        status: task.status.as_str().to_string(),
        project_id: task.project_id,
        project_title: None,
        resurface_on: task.resurface_on,
        completed_at: task.completed_at,
    }
}
```

Update `crates/sfo-services/src/lib.rs`:

```rust
pub mod weekly_review;
pub use weekly_review::WeeklyReviewService;
```

- [ ] **Step 4: Run the service tests**

Run: `cargo test -p sfo-services weekly_review`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add crates/sfo-services/src/lib.rs crates/sfo-services/src/weekly_review.rs
git commit -m "add weekly review service"
```

---

### Task 4: Weekly Review API Routes

**Files:**
- Modify: `crates/sfo-server/src/routes/api.rs`
- Create: `crates/sfo-server/tests/weekly_review_api.rs`

- [ ] **Step 1: Write failing API tests**

Create `crates/sfo-server/tests/weekly_review_api.rs` using the existing server test style:

```rust
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

async fn request_json(app: axum::Router, method: Method, uri: &str, body: Value) -> (StatusCode, Value) {
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
    let bytes = response.into_body().collect().await.expect("body").to_bytes();
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
```

- [ ] **Step 2: Run API tests to verify failure**

Run: `cargo test -p sfo-server weekly_review`

Expected: FAIL because routes do not exist.

- [ ] **Step 3: Add routes and handlers**

Modify imports in `crates/sfo-server/src/routes/api.rs`:

```rust
use sfo_core::{..., WeeklyReviewSummary, WeeklyReviewTask, ...};
use sfo_services::{..., WeeklyReviewService, ...};
```

Add query type:

```rust
#[derive(Debug, Deserialize)]
struct WeeklyReviewQuery {
    date: Option<NaiveDate>,
}
```

Add routes:

```rust
.route("/weekly-review", get(weekly_review))
.route(
    "/weekly-review/tasks/{task_id}/move-to-week",
    post(move_task_to_week),
)
```

Add handlers:

```rust
async fn weekly_review(
    State(state): State<AppState>,
    Query(query): Query<WeeklyReviewQuery>,
) -> Result<Json<WeeklyReviewSummary>, ApiError> {
    let review_date = query.date.unwrap_or_else(|| Utc::now().date_naive());
    let service = WeeklyReviewService::new(state.db);
    Ok(Json(service.summary(review_date).await?))
}

async fn move_task_to_week(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
) -> Result<Json<WeeklyReviewTask>, ApiError> {
    let service = WeeklyReviewService::new(state.db);
    Ok(Json(service.move_task_to_week(parse_task_id(&task_id)?).await?))
}
```

- [ ] **Step 4: Run API tests**

Run: `cargo test -p sfo-server weekly_review`

Expected: PASS.

- [ ] **Step 5: Run Rust workspace tests**

Run: `cargo test --workspace`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add crates/sfo-server/src/routes/api.rs crates/sfo-server/tests/weekly_review_api.rs
git commit -m "add weekly review api"
```

---

### Task 5: Launcher Review View Models And API Helpers

**Files:**
- Modify: `src-tauri/launcher/client.js`
- Modify: `src-tauri/launcher/client.test.mjs`

- [ ] **Step 1: Write failing client tests**

Add imports to `src-tauri/launcher/client.test.mjs`:

```js
  buildWeeklyReviewViewModel,
  buildWeeklyReviewActionFeedback,
```

Update workflow metadata test:

```js
assert.deepEqual(
  WORKFLOWS.map((workflow) => workflow.id),
  ["today", "capture", "process", "review", "settings"],
);
```

Add tests:

```js
test("weekly review view model exposes focus counts and review queues", () => {
  const model = buildWeeklyReviewViewModel({
    review_date: "2026-05-10",
    week_starts_on: "2026-05-04",
    focus_counts: {
      work: { current: 3, cap: 4 },
      personal: { current: 2, cap: 3 },
    },
    weekly_projects: [{ id: "p1", title: "Ship Rust review", category: "work", time_horizon: "week" }],
    available_projects: [
      { id: "p1", title: "Ship Rust review", category: "work", active_this_week: true },
      { id: "p2", title: "Family reset", category: "personal", active_this_week: false },
    ],
    resurface_due: [{ id: "t1", title: "Revisit parked task", when_bucket: "month", resurface_on: "2026-05-09" }],
    completed_tasks: [{ id: "t2", title: "Finished task", completed_at: "2026-05-10T08:00:00Z" }],
  });

  assert.equal(model.reviewLabel, "Week of 2026-05-04");
  assert.equal(model.focusCounts.work.label, "3 / 4 work");
  assert.equal(model.weeklyProjects[0].title, "Ship Rust review");
  assert.equal(model.focusCandidates[1].toggleLabel, "Add to week");
  assert.equal(model.resurfaceDue[0].actionLabel, "Move to Week");
  assert.equal(model.completedTasks[0].actionLabel, "Archive");
});

test("weekly review action feedback keeps irreversible move-to-week copy plain", () => {
  assert.deepEqual(buildWeeklyReviewActionFeedback("move-to-week", "Revisit parked task"), {
    message: "Moved Revisit parked task into this week.",
    undo: null,
  });
});
```

- [ ] **Step 2: Run client tests to verify failure**

Run: `node --test src-tauri/launcher/client.test.mjs`

Expected: FAIL because Review is not in `WORKFLOWS` and helper functions do not exist.

- [ ] **Step 3: Implement view-model helpers**

Modify `src-tauri/launcher/client.js`:

```js
export const WORKFLOWS = [
  { id: "today", label: "Today" },
  { id: "capture", label: "Capture" },
  { id: "process", label: "Process" },
  { id: "review", label: "Review" },
  { id: "settings", label: "Settings" },
];
```

Add `buildWeeklyReviewViewModel(summary)` that returns:

- `reviewLabel`
- `focusCounts.work/personal`
- `weeklyProjects`
- `focusCandidates`
- `resurfaceDue`
- `completedTasks`
- empty-state labels

Add `buildWeeklyReviewActionFeedback(action, title)`:

- `move-to-week`: `{ message: "Moved <title> into this week.", undo: null }`
- `archive`: `{ message: "Archived <title>.", undo: { label: "Restore", action: "restore-task" } }`
- `focus-on`: plain success message
- `focus-off`: plain success message

- [ ] **Step 4: Run client tests**

Run: `node --test src-tauri/launcher/client.test.mjs`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src-tauri/launcher/client.js src-tauri/launcher/client.test.mjs
git commit -m "add weekly review client models"
```

---

### Task 6: Launcher Review Workflow UI

**Files:**
- Modify: `src-tauri/launcher/index.html`
- Modify: `src-tauri/launcher/launcher.js`
- Modify: `src-tauri/launcher/launcher.css`
- Modify: `src-tauri/launcher/workflow-shell.test.mjs`
- Modify: `src-tauri/launcher/mobile-shell.test.mjs`

- [ ] **Step 1: Write failing shell tests**

Update `workflow-shell.test.mjs`:

```js
test("launcher exposes the five top-level workflows", () => {
  const indexHtml = readFileSync(indexHtmlPath, "utf8");

  for (const workflow of ["today", "capture", "process", "review", "settings"]) {
    assert.match(indexHtml, new RegExp(`data-workflow-tab="${workflow}"`));
    assert.match(indexHtml, new RegExp(`data-workflow-panel="${workflow}"`));
  }

  assert.match(indexHtml, /Review/);
});
```

Add test:

```js
test("launcher wires weekly review actions", () => {
  const launcherJs = readFileSync(launcherJsPath, "utf8");

  assert.match(launcherJs, /buildWeeklyReviewViewModel/);
  assert.match(launcherJs, /weekly-review/);
  assert.match(launcherJs, /data-review-action/);
  assert.match(launcherJs, /move-to-week/);
});
```

Update `mobile-shell.test.mjs`:

```js
assert.match(launcherCss, /@media \(max-width: 1024px\)[\s\S]*\.workflow-nav[\s\S]*repeat\(2, minmax\(0, 1fr\)\)/);
assert.match(launcherCss, /\.review-grid/);
```

- [ ] **Step 2: Run shell tests to verify failure**

Run: `node --test src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs`

Expected: FAIL because the Review workflow panel/actions do not exist.

- [ ] **Step 3: Add Review HTML**

Modify `src-tauri/launcher/index.html`:

- Add Review tab between Process and Settings.
- Add `section` with `data-workflow-panel="review"` and IDs:
  - `review-date-label`
  - `review-refresh`
  - `review-work-count`
  - `review-personal-count`
  - `review-weekly-projects`
  - `review-focus-candidates`
  - `review-resurface-due`
  - `review-completed-tasks`

- [ ] **Step 4: Add Review render and action wiring**

Modify imports in `launcher.js`:

```js
  buildWeeklyReviewActionFeedback,
  buildWeeklyReviewViewModel,
```

Add elements for Review IDs.

Add `weeklyReviewSummary` to loaded state if useful.

Update `connectAndLoad()` Promise:

```js
const [summary, inboxContainers, projectsPage, weeklyReview] = await Promise.all([
  requestJson(window.fetch.bind(window), settings, "/api/v1/bootstrap"),
  requestJson(window.fetch.bind(window), settings, "/api/v1/inbox/containers"),
  requestJson(window.fetch.bind(window), settings, "/api/v1/projects?page=1&page_size=100"),
  requestJson(window.fetch.bind(window), settings, "/api/v1/weekly-review"),
]);
```

Add render helpers:

- `renderWeeklyReview(model)`
- `reviewProjectCard(project)`
- `reviewFocusCandidate(candidate)`
- `reviewTaskRow(task, action)`
- `reloadWeeklyReview()`

Wire actions:

- `focus-toggle`: PATCH `/api/v1/projects/${id}` with `{ active_this_week: nextActive }`
- `move-to-week`: POST `/api/v1/weekly-review/tasks/${id}/move-to-week`
- `archive-task`: POST `/api/v1/tasks/${id}/archive`
- `restore-task`: POST `/api/v1/tasks/${id}/restore`
- `review-refresh`: reload weekly review

- [ ] **Step 5: Add Review CSS**

Modify `launcher.css`:

- `.review-grid`
- `.review-count-grid`
- `.review-count-card`
- `.review-project-card`
- `.review-task-row`
- `.review-actions`

Use existing `--sfo-radius-button` for buttons and avoid overly rounded new controls.

- [ ] **Step 6: Run shell tests**

Run: `node --test src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs`

Expected: PASS.

- [ ] **Step 7: Run all launcher tests and syntax checks**

Run:

```bash
node --test src-tauri/launcher/*.test.mjs
node --check src-tauri/launcher/client.js
node --check src-tauri/launcher/launcher.js
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src-tauri/launcher/index.html src-tauri/launcher/launcher.js src-tauri/launcher/launcher.css src-tauri/launcher/workflow-shell.test.mjs src-tauri/launcher/mobile-shell.test.mjs
git commit -m "add weekly review workflow shell"
```

---

### Task 7: Documentation And Runtime Verification

**Files:**
- Modify: `docs/rust_rewrite_parity_review.md`
- Modify: `docs/workflow_shell_ux_review.md`

- [ ] **Step 1: Update docs**

Update parity/review docs to record:

- Weekly Review API exists.
- Review workflow shell exists.
- Move-to-week and completed-task archive are available.
- Later slices still include persisted review notes, week calendar, long-range board, and physical iPhone signing.

- [ ] **Step 2: Run full verification**

Run:

```bash
node --test src-tauri/launcher/*.test.mjs
node --check src-tauri/launcher/client.js
node --check src-tauri/launcher/launcher.js
cargo test --workspace
git diff --check
```

Expected: all pass.

- [ ] **Step 3: Run macOS runtime smoke**

Start a disposable server:

```bash
SFO_RUST_BIND=127.0.0.1:18089 SFO_RUST_DATABASE_URL=sqlite:///private/tmp/sfo-rust-weekly-review.db cargo run -p sfo-server
```

Seed realistic projects/tasks with `curl` or a short local Node script:

- 2 active work weekly projects.
- 1 active personal weekly project.
- 1 inactive work candidate.
- 1 due resurface task with `resurface_on <= today`.
- 1 completed task this week.

Open the dev shell:

```bash
scripts/run_tauri_dev_shell.sh
```

Manual checks:

- Review tab appears.
- Focus counts show work/personal caps.
- Focus toggle respects cap behavior.
- Move-to-week removes the task from due resurface.
- Archive removes the completed task from cleanup.
- Today still renders after weekly review actions.

- [ ] **Step 4: Run iOS simulator smoke if Xcode simulator is available**

Run:

```bash
/Users/rcd58/sfo/.worktrees/rust-rewrite/scripts/build_tauri_ios_simulator.sh
xcrun simctl install booted "/Users/rcd58/sfo/.worktrees/rust-rewrite/src-tauri/gen/apple/build/arm64-sim/Start Finishing Organiser.app"
xcrun simctl launch booted com.rcd58.sfo
```

Manual checks:

- Five-tab workflow nav remains usable.
- Review content does not overflow horizontally.
- Settings input focus behavior remains fixed.

- [ ] **Step 5: Commit docs and any final fixes**

```bash
git add docs/rust_rewrite_parity_review.md docs/workflow_shell_ux_review.md
git commit -m "docs: record weekly review progress"
```

- [ ] **Step 6: Push branch**

```bash
git push origin codex/rust-rewrite
```

Expected: branch pushed successfully.
