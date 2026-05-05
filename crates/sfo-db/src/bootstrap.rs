use chrono::NaiveDate;
use sfo_core::{Block, BootstrapInboxSummary, Project, Task};

use crate::planning::{ProjectRow, TaskRow};
use crate::schedule::BlockRow;
use crate::DbError;

pub async fn active_weekly_projects(pool: &sqlx::SqlitePool) -> Result<Vec<Project>, DbError> {
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

pub async fn today_tasks(pool: &sqlx::SqlitePool, _today: NaiveDate) -> Result<Vec<Task>, DbError> {
    let rows = sqlx::query_as::<_, TaskRow>(
        r#"
        SELECT * FROM tasks
        WHERE when_bucket = 'today'
          AND status IN ('pending', 'in_progress')
        ORDER BY block_type IS NULL ASC, block_type ASC,
                 priority IS NULL ASC, priority ASC, created_at DESC
        "#,
    )
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Task::try_from).collect()
}

pub async fn today_blocks(
    pool: &sqlx::SqlitePool,
    today: NaiveDate,
) -> Result<Vec<Block>, DbError> {
    let rows = sqlx::query_as::<_, BlockRow>(
        r#"
        SELECT * FROM blocks
        WHERE date = ?
        ORDER BY start_time IS NULL ASC, start_time ASC, created_at ASC
        "#,
    )
    .bind(today.to_string())
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Block::try_from).collect()
}

pub async fn inbox_summary(pool: &sqlx::SqlitePool) -> Result<BootstrapInboxSummary, DbError> {
    let counts = crate::inbox::counts(pool).await?;
    Ok(BootstrapInboxSummary {
        unprocessed: counts.unprocessed,
        learn_explore: counts.learn_explore,
        enjoy_recover: counts.enjoy_recover,
        park_let_go: counts.park_let_go,
        recycle_bin: counts.recycle_bin,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::planning::{create_project, create_task, update_task};
    use crate::schedule::create_block;
    use crate::{connect, run_migrations, DbConfig};
    use chrono::{NaiveDate, NaiveTime};
    use sfo_core::{
        BlockCreate, BlockType, ProjectCategory, ProjectCreate, TaskCreate, TaskStatus, WhenBucket,
        INBOX_INTENT_LEARN_EXPLORE, INBOX_INTENT_UNPROCESSED,
    };

    async fn migrated_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn bootstrap_queries_return_home_dashboard_rows() {
        let pool = migrated_pool().await;
        let today = NaiveDate::from_ymd_opt(2026, 5, 6).expect("today");
        let project = create_project(
            &pool,
            ProjectCreate {
                title: "Weekly Project".to_string(),
                description: None,
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
        .expect("project");
        create_task(
            &pool,
            TaskCreate {
                verb_noun: "Do today".to_string(),
                project_id: Some(project.id),
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Today,
                block_type: Some(BlockType::Focus),
                duration_minutes: Some(30),
                priority: Some(1),
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            },
        )
        .await
        .expect("today task");
        create_task(
            &pool,
            TaskCreate {
                verb_noun: "Inbox item".to_string(),
                project_id: None,
                description: None,
                in_inbox: true,
                when_bucket: WhenBucket::Later,
                block_type: None,
                duration_minutes: None,
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            },
        )
        .await
        .expect("inbox task");
        let mut learning = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Read later".to_string(),
                project_id: None,
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Later,
                block_type: None,
                duration_minutes: None,
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            },
        )
        .await
        .expect("learning task");
        learning.intake_container = INBOX_INTENT_LEARN_EXPLORE.to_string();
        learning.intake_intent = INBOX_INTENT_UNPROCESSED.to_string();
        update_task(&pool, &learning)
            .await
            .expect("update learning");
        create_block(
            &pool,
            BlockCreate {
                title: Some("Focus block".to_string()),
                date: today,
                start_time: Some(NaiveTime::from_hms_opt(9, 0, 0).expect("start")),
                end_time: Some(NaiveTime::from_hms_opt(10, 0, 0).expect("end")),
                block_type: BlockType::Focus,
                project_id: Some(project.id),
                task_id: None,
                notes: None,
            },
        )
        .await
        .expect("block");

        assert_eq!(
            active_weekly_projects(&pool).await.expect("projects").len(),
            1
        );
        assert_eq!(today_tasks(&pool, today).await.expect("tasks").len(), 1);
        assert_eq!(today_blocks(&pool, today).await.expect("blocks").len(), 1);
        let inbox = inbox_summary(&pool).await.expect("inbox summary");
        assert_eq!(inbox.unprocessed, 1);
        assert_eq!(inbox.learn_explore, 1);
    }

    #[tokio::test]
    async fn inbox_summary_counts_recycle_bin() {
        let pool = migrated_pool().await;
        let mut task = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Deleted inbox item".to_string(),
                project_id: None,
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Later,
                block_type: None,
                duration_minutes: None,
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            },
        )
        .await
        .expect("task");
        task.archived_from_inbox = true;
        task.status = TaskStatus::Archived;
        update_task(&pool, &task).await.expect("archive task");

        let inbox = inbox_summary(&pool).await.expect("summary");

        assert_eq!(inbox.recycle_bin, 1);
    }
}
