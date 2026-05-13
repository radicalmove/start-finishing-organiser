use chrono::{NaiveDate, Utc};
use sfo_core::{Project, ProjectCategory, Task, TaskId, WhenBucket};

use crate::planning::{ProjectRow, TaskRow};
use crate::DbError;

pub async fn focus_count(
    pool: &sqlx::SqlitePool,
    category: ProjectCategory,
) -> Result<i64, DbError> {
    crate::planning::count_active_projects_by_category(pool, category).await
}

pub async fn weekly_projects(pool: &sqlx::SqlitePool) -> Result<Vec<Project>, DbError> {
    let rows = sqlx::query_as::<_, ProjectRow>(
        r#"
        SELECT * FROM projects
        WHERE active_this_week = 1
          AND status != 'archived'
        ORDER BY category ASC, created_at DESC
        "#,
    )
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Project::try_from).collect()
}

pub async fn available_projects(pool: &sqlx::SqlitePool) -> Result<Vec<Project>, DbError> {
    let rows = sqlx::query_as::<_, ProjectRow>(
        r#"
        SELECT * FROM projects
        WHERE status = 'active'
        ORDER BY active_this_week DESC, category ASC, created_at DESC
        "#,
    )
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Project::try_from).collect()
}

pub async fn due_resurface_tasks(
    pool: &sqlx::SqlitePool,
    review_date: NaiveDate,
) -> Result<Vec<Task>, DbError> {
    let rows = sqlx::query_as::<_, TaskRow>(
        r#"
        SELECT * FROM tasks
        WHERE resurface_on IS NOT NULL
          AND resurface_on <= ?
          AND status NOT IN ('done', 'archived')
          AND in_inbox = 0
        ORDER BY resurface_on ASC, created_at ASC
        "#,
    )
    .bind(review_date.to_string())
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Task::try_from).collect()
}

pub async fn completed_tasks_since(
    pool: &sqlx::SqlitePool,
    week_starts_on: NaiveDate,
) -> Result<Vec<Task>, DbError> {
    let rows = sqlx::query_as::<_, TaskRow>(
        r#"
        SELECT * FROM tasks
        WHERE status = 'done'
          AND completed_at IS NOT NULL
          AND completed_at >= ?
        ORDER BY completed_at DESC, created_at DESC
        "#,
    )
    .bind(format!("{week_starts_on}T00:00:00+00:00"))
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Task::try_from).collect()
}

pub async fn move_task_to_week(
    pool: &sqlx::SqlitePool,
    id: TaskId,
) -> Result<Option<Task>, DbError> {
    sqlx::query(
        r#"
        UPDATE tasks
        SET when_bucket = ?, resurface_on = NULL, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(WhenBucket::Week.as_str())
    .bind(Utc::now().to_rfc3339())
    .bind(id.to_string())
    .execute(pool)
    .await?;

    crate::planning::get_task(pool, id).await
}

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
        let active_project = crate::planning::create_project(
            &pool,
            ProjectCreate {
                title: "Weekly work".to_string(),
                description: None,
                category: ProjectCategory::Work,
                size: None,
                time_horizon: Some("week".to_string()),
                start_date: None,
                target_date: None,
                level_of_success: None,
                why_link_text: None,
                drag_points_notes: None,
                gates_notes: None,
                budget_notes: None,
                active_this_week: true,
            },
        )
        .await
        .expect("project");

        let due_task = crate::planning::create_task(
            &pool,
            TaskCreate {
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
            },
        )
        .await
        .expect("due task");

        sqlx::query("UPDATE tasks SET resurface_on = ? WHERE id = ?")
            .bind("2026-05-09")
            .bind(due_task.id.to_string())
            .execute(&pool)
            .await
            .expect("set resurface");

        let completed_task = crate::planning::create_task(
            &pool,
            TaskCreate {
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
            },
        )
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
        let task = crate::planning::create_task(
            &pool,
            TaskCreate {
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
            },
        )
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
