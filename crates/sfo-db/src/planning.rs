use chrono::{DateTime, NaiveDate, Utc};
use sfo_core::{
    Page, Project, ProjectCategory, ProjectCreate, ProjectId, ProjectStatus, Task, TaskCreate,
    TaskId, TaskStatus, INBOX_INTENT_UNPROCESSED,
};
use sqlx::FromRow;
use std::str::FromStr;

use crate::DbError;

pub async fn create_project(
    pool: &sqlx::SqlitePool,
    payload: ProjectCreate,
) -> Result<Project, DbError> {
    let id = ProjectId::new();
    let size = payload.size.map(|value| value.as_str().to_string());
    let target_date = format_date(payload.target_date);
    let level_of_success = payload
        .level_of_success
        .map(|value| value.as_str().to_string());

    sqlx::query(
        r#"
        INSERT INTO projects (
            id, title, description, category, status, size, time_horizon, target_date,
            level_of_success, why_link_text, active_this_week
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
    .bind(id.to_string())
    .bind(payload.title)
    .bind(payload.description)
    .bind(payload.category.as_str())
    .bind(ProjectStatus::Active.as_str())
    .bind(size)
    .bind(payload.time_horizon)
    .bind(target_date)
    .bind(level_of_success)
    .bind(payload.why_link_text)
    .bind(bool_to_i64(payload.active_this_week))
    .execute(pool)
    .await?;

    get_project(pool, id)
        .await?
        .ok_or_else(|| DbError::InvalidData("created project could not be loaded".to_string()))
}

pub async fn count_active_projects_by_category(
    pool: &sqlx::SqlitePool,
    category: ProjectCategory,
) -> Result<i64, DbError> {
    let count = sqlx::query_scalar(
        "SELECT COUNT(*) FROM projects WHERE category = ? AND active_this_week = 1",
    )
    .bind(category.as_str())
    .fetch_one(pool)
    .await?;

    Ok(count)
}

pub async fn list_projects(
    pool: &sqlx::SqlitePool,
    page: i64,
    page_size: i64,
) -> Result<Page<Project>, DbError> {
    let page_size = normalize_page_size(page_size);
    let total: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM projects")
        .fetch_one(pool)
        .await?;
    let page = resolve_page(page, page_size, total);
    let rows = sqlx::query_as::<_, ProjectRow>(
        r#"
        SELECT * FROM projects
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        "#,
    )
    .bind(page_size)
    .bind((page - 1) * page_size)
    .fetch_all(pool)
    .await?;
    let items = rows
        .into_iter()
        .map(Project::try_from)
        .collect::<Result<Vec<_>, _>>()?;

    Ok(Page::new(items, page, page_size, total))
}

pub async fn get_project(
    pool: &sqlx::SqlitePool,
    id: ProjectId,
) -> Result<Option<Project>, DbError> {
    let row = sqlx::query_as::<_, ProjectRow>("SELECT * FROM projects WHERE id = ?")
        .bind(id.to_string())
        .fetch_optional(pool)
        .await?;

    row.map(Project::try_from).transpose()
}

pub async fn update_project(
    pool: &sqlx::SqlitePool,
    project: &Project,
) -> Result<Project, DbError> {
    let size = project.size.map(|value| value.as_str().to_string());
    let target_date = format_date(project.target_date);
    let level_of_success = project
        .level_of_success
        .map(|value| value.as_str().to_string());

    sqlx::query(
        r#"
        UPDATE projects
        SET title = ?, description = ?, category = ?, status = ?, size = ?,
            time_horizon = ?, target_date = ?, level_of_success = ?, why_link_text = ?,
            active_this_week = ?, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(&project.title)
    .bind(&project.description)
    .bind(project.category.as_str())
    .bind(project.status.as_str())
    .bind(size)
    .bind(&project.time_horizon)
    .bind(target_date)
    .bind(level_of_success)
    .bind(&project.why_link_text)
    .bind(bool_to_i64(project.active_this_week))
    .bind(now_text())
    .bind(project.id.to_string())
    .execute(pool)
    .await?;

    get_project(pool, project.id)
        .await?
        .ok_or_else(|| DbError::InvalidData("updated project could not be loaded".to_string()))
}

pub async fn delete_project(pool: &sqlx::SqlitePool, id: ProjectId) -> Result<bool, DbError> {
    let result = sqlx::query("DELETE FROM projects WHERE id = ?")
        .bind(id.to_string())
        .execute(pool)
        .await?;

    Ok(result.rows_affected() > 0)
}

pub async fn create_task(pool: &sqlx::SqlitePool, payload: TaskCreate) -> Result<Task, DbError> {
    let id = TaskId::new();
    let block_type = payload.block_type.map(|value| value.as_str().to_string());
    let alignment = payload.alignment.map(|value| value.as_str().to_string());
    let scheduled_for = format_date(payload.scheduled_for);

    sqlx::query(
        r#"
        INSERT INTO tasks (
            id, project_id, verb_noun, description, in_inbox, archived_from_inbox,
            intake_intent, intake_container, when_bucket, block_type, duration_minutes,
            priority, frog, alignment, first_action, status, scheduled_for
        )
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
    .bind(id.to_string())
    .bind(payload.project_id.map(|value| value.to_string()))
    .bind(payload.verb_noun)
    .bind(payload.description)
    .bind(bool_to_i64(payload.in_inbox))
    .bind(INBOX_INTENT_UNPROCESSED)
    .bind(INBOX_INTENT_UNPROCESSED)
    .bind(payload.when_bucket.as_str())
    .bind(block_type)
    .bind(payload.duration_minutes)
    .bind(payload.priority)
    .bind(bool_to_i64(payload.frog))
    .bind(alignment)
    .bind(payload.first_action)
    .bind(TaskStatus::Pending.as_str())
    .bind(scheduled_for)
    .execute(pool)
    .await?;

    get_task(pool, id)
        .await?
        .ok_or_else(|| DbError::InvalidData("created task could not be loaded".to_string()))
}

pub async fn list_tasks(
    pool: &sqlx::SqlitePool,
    page: i64,
    page_size: i64,
) -> Result<Page<Task>, DbError> {
    let page_size = normalize_page_size(page_size);
    let total: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM tasks")
        .fetch_one(pool)
        .await?;
    let page = resolve_page(page, page_size, total);
    let rows = sqlx::query_as::<_, TaskRow>(
        r#"
        SELECT * FROM tasks
        ORDER BY when_bucket ASC, priority IS NULL ASC, priority ASC, created_at DESC
        LIMIT ? OFFSET ?
        "#,
    )
    .bind(page_size)
    .bind((page - 1) * page_size)
    .fetch_all(pool)
    .await?;
    let items = rows
        .into_iter()
        .map(Task::try_from)
        .collect::<Result<Vec<_>, _>>()?;

    Ok(Page::new(items, page, page_size, total))
}

pub async fn get_task(pool: &sqlx::SqlitePool, id: TaskId) -> Result<Option<Task>, DbError> {
    let row = sqlx::query_as::<_, TaskRow>("SELECT * FROM tasks WHERE id = ?")
        .bind(id.to_string())
        .fetch_optional(pool)
        .await?;

    row.map(Task::try_from).transpose()
}

pub async fn update_task(pool: &sqlx::SqlitePool, task: &Task) -> Result<Task, DbError> {
    let project_id = task.project_id.map(|value| value.to_string());
    let intake_processed_at = format_datetime(task.intake_processed_at);
    let block_type = task.block_type.map(|value| value.as_str().to_string());
    let alignment = task.alignment.map(|value| value.as_str().to_string());
    let scheduled_for = format_date(task.scheduled_for);
    let resurface_on = format_date(task.resurface_on);
    let completed_at = format_datetime(task.completed_at);

    sqlx::query(
        r#"
        UPDATE tasks
        SET project_id = ?, verb_noun = ?, description = ?, in_inbox = ?,
            archived_from_inbox = ?, intake_intent = ?, intake_container = ?,
            intake_processed_at = ?, when_bucket = ?, block_type = ?, duration_minutes = ?,
            priority = ?, frog = ?, alignment = ?, first_action = ?, status = ?,
            scheduled_for = ?, resurface_on = ?, completed_at = ?, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(project_id)
    .bind(&task.verb_noun)
    .bind(&task.description)
    .bind(bool_to_i64(task.in_inbox))
    .bind(bool_to_i64(task.archived_from_inbox))
    .bind(&task.intake_intent)
    .bind(&task.intake_container)
    .bind(intake_processed_at)
    .bind(task.when_bucket.as_str())
    .bind(block_type)
    .bind(task.duration_minutes)
    .bind(task.priority)
    .bind(bool_to_i64(task.frog))
    .bind(alignment)
    .bind(&task.first_action)
    .bind(task.status.as_str())
    .bind(scheduled_for)
    .bind(resurface_on)
    .bind(completed_at)
    .bind(now_text())
    .bind(task.id.to_string())
    .execute(pool)
    .await?;

    get_task(pool, task.id)
        .await?
        .ok_or_else(|| DbError::InvalidData("updated task could not be loaded".to_string()))
}

pub async fn delete_task(pool: &sqlx::SqlitePool, id: TaskId) -> Result<bool, DbError> {
    let result = sqlx::query("DELETE FROM tasks WHERE id = ?")
        .bind(id.to_string())
        .execute(pool)
        .await?;

    Ok(result.rows_affected() > 0)
}

#[derive(Debug, FromRow)]
pub(crate) struct ProjectRow {
    id: String,
    title: String,
    description: Option<String>,
    category: String,
    status: String,
    size: Option<String>,
    time_horizon: Option<String>,
    target_date: Option<String>,
    level_of_success: Option<String>,
    why_link_text: Option<String>,
    active_this_week: i64,
    created_at: String,
    updated_at: Option<String>,
}

impl TryFrom<ProjectRow> for Project {
    type Error = DbError;

    fn try_from(row: ProjectRow) -> Result<Self, Self::Error> {
        Ok(Self {
            id: parse_id(&row.id)?,
            title: row.title,
            description: row.description,
            category: parse_enum(&row.category)?,
            status: parse_enum(&row.status)?,
            size: parse_optional_enum(row.size)?,
            time_horizon: row.time_horizon,
            target_date: parse_optional_date(row.target_date)?,
            level_of_success: parse_optional_enum(row.level_of_success)?,
            why_link_text: row.why_link_text,
            active_this_week: i64_to_bool(row.active_this_week),
            created_at: parse_datetime(&row.created_at)?,
            updated_at: parse_optional_datetime(row.updated_at)?,
        })
    }
}

#[derive(Debug, FromRow)]
pub(crate) struct TaskRow {
    id: String,
    project_id: Option<String>,
    verb_noun: String,
    description: Option<String>,
    in_inbox: i64,
    archived_from_inbox: i64,
    intake_intent: String,
    intake_container: String,
    intake_processed_at: Option<String>,
    when_bucket: String,
    block_type: Option<String>,
    duration_minutes: Option<i64>,
    priority: Option<i64>,
    frog: i64,
    alignment: Option<String>,
    first_action: Option<String>,
    status: String,
    scheduled_for: Option<String>,
    resurface_on: Option<String>,
    completed_at: Option<String>,
    created_at: String,
    updated_at: Option<String>,
}

impl TryFrom<TaskRow> for Task {
    type Error = DbError;

    fn try_from(row: TaskRow) -> Result<Self, Self::Error> {
        Ok(Self {
            id: parse_id(&row.id)?,
            project_id: parse_optional_id(row.project_id)?,
            verb_noun: row.verb_noun,
            description: row.description,
            in_inbox: i64_to_bool(row.in_inbox),
            archived_from_inbox: i64_to_bool(row.archived_from_inbox),
            intake_intent: row.intake_intent,
            intake_container: row.intake_container,
            intake_processed_at: parse_optional_datetime(row.intake_processed_at)?,
            when_bucket: parse_enum(&row.when_bucket)?,
            block_type: parse_optional_enum(row.block_type)?,
            duration_minutes: row.duration_minutes,
            priority: row.priority,
            frog: i64_to_bool(row.frog),
            alignment: parse_optional_enum(row.alignment)?,
            first_action: row.first_action,
            status: parse_enum(&row.status)?,
            scheduled_for: parse_optional_date(row.scheduled_for)?,
            resurface_on: parse_optional_date(row.resurface_on)?,
            completed_at: parse_optional_datetime(row.completed_at)?,
            created_at: parse_datetime(&row.created_at)?,
            updated_at: parse_optional_datetime(row.updated_at)?,
        })
    }
}

fn normalize_page_size(page_size: i64) -> i64 {
    page_size.clamp(1, 200)
}

fn resolve_page(page: i64, page_size: i64, total: i64) -> i64 {
    let total_pages = if total > 0 {
        (total + page_size - 1) / page_size
    } else {
        1
    };
    page.clamp(1, total_pages)
}

fn bool_to_i64(value: bool) -> i64 {
    i64::from(value)
}

fn i64_to_bool(value: i64) -> bool {
    value != 0
}

fn now_text() -> String {
    Utc::now().to_rfc3339()
}

fn format_datetime(value: Option<DateTime<Utc>>) -> Option<String> {
    value.map(|date_time| date_time.to_rfc3339())
}

fn format_date(value: Option<NaiveDate>) -> Option<String> {
    value.map(|date| date.to_string())
}

fn parse_id<T>(value: &str) -> Result<T, DbError>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    value
        .parse::<T>()
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_optional_id<T>(value: Option<String>) -> Result<Option<T>, DbError>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    value.as_deref().map(parse_id).transpose()
}

fn parse_enum<T>(value: &str) -> Result<T, DbError>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    value
        .parse::<T>()
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_optional_enum<T>(value: Option<String>) -> Result<Option<T>, DbError>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    value.as_deref().map(parse_enum).transpose()
}

fn parse_datetime(value: &str) -> Result<DateTime<Utc>, DbError> {
    DateTime::parse_from_rfc3339(value)
        .map(|date_time| date_time.with_timezone(&Utc))
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_optional_datetime(value: Option<String>) -> Result<Option<DateTime<Utc>>, DbError> {
    value.as_deref().map(parse_datetime).transpose()
}

fn parse_optional_date(value: Option<String>) -> Result<Option<NaiveDate>, DbError> {
    value
        .as_deref()
        .map(|date| {
            NaiveDate::parse_from_str(date, "%Y-%m-%d")
                .map_err(|error| DbError::InvalidData(error.to_string()))
        })
        .transpose()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{connect, run_migrations, DbConfig};
    use sfo_core::{ProjectStatus, TaskStatus, WhenBucket};

    async fn migrated_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn projects_can_be_inserted_listed_updated_and_deleted() {
        let pool = migrated_pool().await;
        let project = create_project(
            &pool,
            ProjectCreate {
                title: "Project A".to_string(),
                description: Some("Scope".to_string()),
                category: ProjectCategory::Work,
                size: None,
                time_horizon: None,
                target_date: None,
                level_of_success: None,
                why_link_text: None,
                active_this_week: true,
            },
        )
        .await
        .expect("create project");

        assert_eq!(project.title, "Project A");
        assert_eq!(
            count_active_projects_by_category(&pool, ProjectCategory::Work)
                .await
                .expect("count active projects"),
            1
        );

        let page = list_projects(&pool, 1, 10).await.expect("list projects");
        assert_eq!(page.total, 1);
        assert_eq!(page.items[0].id, project.id);

        let mut updated = project;
        updated.title = "Updated".to_string();
        updated.status = ProjectStatus::Paused;
        let updated = update_project(&pool, &updated)
            .await
            .expect("update project");
        assert_eq!(updated.title, "Updated");
        assert_eq!(updated.status, ProjectStatus::Paused);

        assert!(delete_project(&pool, updated.id)
            .await
            .expect("delete project"));
        assert!(get_project(&pool, updated.id)
            .await
            .expect("get deleted project")
            .is_none());
    }

    #[tokio::test]
    async fn tasks_can_be_inserted_listed_updated_and_deleted() {
        let pool = migrated_pool().await;
        let task = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Draft test plan".to_string(),
                project_id: None,
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Today,
                block_type: None,
                duration_minutes: None,
                priority: Some(1),
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            },
        )
        .await
        .expect("create task");

        let page = list_tasks(&pool, 1, 10).await.expect("list tasks");
        assert_eq!(page.total, 1);
        assert_eq!(page.items[0].id, task.id);

        let mut updated = task;
        updated.status = TaskStatus::Done;
        updated.frog = true;
        let updated = update_task(&pool, &updated).await.expect("update task");
        assert_eq!(updated.status, TaskStatus::Done);
        assert!(updated.frog);

        assert!(delete_task(&pool, updated.id).await.expect("delete task"));
        assert!(get_task(&pool, updated.id)
            .await
            .expect("get deleted task")
            .is_none());
    }
}
