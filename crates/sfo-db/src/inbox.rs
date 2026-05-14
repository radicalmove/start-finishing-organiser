use chrono::{DateTime, Utc};
use sfo_core::{
    InboxContainerCounts, InboxContainers, Task, INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_LEARN_EXPLORE, INBOX_INTENT_PARK_LET_GO, INBOX_INTENT_UNPROCESSED,
};

use crate::planning::TaskRow;
use crate::DbError;

pub async fn containers(pool: &sqlx::SqlitePool) -> Result<InboxContainers, DbError> {
    promote_due_parked_items(pool, Utc::now()).await?;
    Ok(InboxContainers {
        counts: counts(pool).await?,
        unprocessed: active_unprocessed_items(pool).await?,
        learning: active_container_items(pool, INBOX_INTENT_LEARN_EXPLORE).await?,
        enjoy: active_container_items(pool, INBOX_INTENT_ENJOY_RECOVER).await?,
        parked: active_container_items(pool, INBOX_INTENT_PARK_LET_GO).await?,
        recycle_bin: recycle_bin_items(pool).await?,
    })
}

pub async fn counts(pool: &sqlx::SqlitePool) -> Result<InboxContainerCounts, DbError> {
    promote_due_parked_items(pool, Utc::now()).await?;
    Ok(InboxContainerCounts {
        unprocessed: count_active_inbox(pool).await?,
        learn_explore: count_active_container(pool, INBOX_INTENT_LEARN_EXPLORE).await?,
        enjoy_recover: count_active_container(pool, INBOX_INTENT_ENJOY_RECOVER).await?,
        park_let_go: count_active_container(pool, INBOX_INTENT_PARK_LET_GO).await?,
        recycle_bin: count_recycle_bin(pool).await?,
    })
}

pub async fn promote_due_parked_items(
    pool: &sqlx::SqlitePool,
    now: DateTime<Utc>,
) -> Result<i64, DbError> {
    let result = sqlx::query(
        r#"
        UPDATE tasks
        SET in_inbox = 1,
            archived_from_inbox = 0,
            intake_intent = ?,
            intake_container = ?,
            intake_processed_at = NULL,
            when_bucket = 'later',
            status = 'pending',
            completed_at = NULL,
            parked_until = NULL,
            updated_at = ?
        WHERE in_inbox = 0
          AND archived_from_inbox = 0
          AND intake_container = ?
          AND status IN ('pending', 'in_progress')
          AND parked_until IS NOT NULL
          AND parked_until <= ?
        "#,
    )
    .bind(INBOX_INTENT_UNPROCESSED)
    .bind(INBOX_INTENT_UNPROCESSED)
    .bind(now.to_rfc3339())
    .bind(INBOX_INTENT_PARK_LET_GO)
    .bind(now.to_rfc3339())
    .execute(pool)
    .await?;

    Ok(i64::try_from(result.rows_affected())
        .map_err(|error| DbError::InvalidData(error.to_string()))?)
}

async fn active_unprocessed_items(pool: &sqlx::SqlitePool) -> Result<Vec<Task>, DbError> {
    let rows = sqlx::query_as::<_, TaskRow>(
        r#"
        SELECT * FROM tasks
        WHERE in_inbox = 1
          AND status IN ('pending', 'in_progress')
        ORDER BY created_at DESC
        "#,
    )
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Task::try_from).collect()
}

async fn active_container_items(
    pool: &sqlx::SqlitePool,
    container: &str,
) -> Result<Vec<Task>, DbError> {
    let rows = sqlx::query_as::<_, TaskRow>(
        r#"
        SELECT * FROM tasks
        WHERE intake_container = ?
          AND status IN ('pending', 'in_progress')
        ORDER BY created_at DESC
        "#,
    )
    .bind(container)
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Task::try_from).collect()
}

async fn recycle_bin_items(pool: &sqlx::SqlitePool) -> Result<Vec<Task>, DbError> {
    let rows = sqlx::query_as::<_, TaskRow>(
        r#"
        SELECT * FROM tasks
        WHERE archived_from_inbox = 1
          AND status = 'archived'
        ORDER BY created_at DESC
        "#,
    )
    .fetch_all(pool)
    .await?;

    rows.into_iter().map(Task::try_from).collect()
}

async fn count_active_inbox(pool: &sqlx::SqlitePool) -> Result<i64, DbError> {
    let count = sqlx::query_scalar(
        r#"
        SELECT COUNT(*) FROM tasks
        WHERE in_inbox = 1
          AND status IN ('pending', 'in_progress')
        "#,
    )
    .fetch_one(pool)
    .await?;
    Ok(count)
}

async fn count_active_container(pool: &sqlx::SqlitePool, container: &str) -> Result<i64, DbError> {
    let count = sqlx::query_scalar(
        r#"
        SELECT COUNT(*) FROM tasks
        WHERE intake_container = ?
          AND status IN ('pending', 'in_progress')
        "#,
    )
    .bind(container)
    .fetch_one(pool)
    .await?;
    Ok(count)
}

async fn count_recycle_bin(pool: &sqlx::SqlitePool) -> Result<i64, DbError> {
    let count = sqlx::query_scalar(
        r#"
        SELECT COUNT(*) FROM tasks
        WHERE archived_from_inbox = 1
          AND status = 'archived'
        "#,
    )
    .fetch_one(pool)
    .await?;
    Ok(count)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::planning::{create_task, update_task};
    use crate::{connect, run_migrations, DbConfig};
    use sfo_core::{TaskCreate, TaskStatus, WhenBucket, INBOX_INTENT_UNPROCESSED};

    async fn migrated_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn containers_return_active_items_and_recycle_bin() {
        let pool = migrated_pool().await;
        let unprocessed = create_task(
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
                owner_type: Default::default(),
            },
        )
        .await
        .expect("inbox task");
        let mut learning = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Learn thing".to_string(),
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
                owner_type: Default::default(),
            },
        )
        .await
        .expect("learning task");
        learning.intake_intent = INBOX_INTENT_LEARN_EXPLORE.to_string();
        learning.intake_container = INBOX_INTENT_LEARN_EXPLORE.to_string();
        update_task(&pool, &learning)
            .await
            .expect("update learning");

        let mut recycled = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Recycle thing".to_string(),
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
                owner_type: Default::default(),
            },
        )
        .await
        .expect("recycled task");
        recycled.intake_intent = INBOX_INTENT_UNPROCESSED.to_string();
        recycled.intake_container = INBOX_INTENT_UNPROCESSED.to_string();
        recycled.archived_from_inbox = true;
        recycled.status = TaskStatus::Archived;
        update_task(&pool, &recycled).await.expect("update recycle");

        let mut scheduled_parked = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Scheduled parked thing".to_string(),
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
                owner_type: Default::default(),
            },
        )
        .await
        .expect("scheduled parked task");
        scheduled_parked.intake_intent = INBOX_INTENT_PARK_LET_GO.to_string();
        scheduled_parked.intake_container = INBOX_INTENT_PARK_LET_GO.to_string();
        scheduled_parked.parked_until = Some("2099-01-01T09:00:00Z".parse().unwrap());
        update_task(&pool, &scheduled_parked)
            .await
            .expect("update scheduled parked");

        let containers = containers(&pool).await.expect("containers");

        assert_eq!(containers.counts.unprocessed, 1);
        assert_eq!(containers.counts.learn_explore, 1);
        assert_eq!(containers.counts.park_let_go, 1);
        assert_eq!(containers.counts.recycle_bin, 1);
        assert_eq!(containers.unprocessed[0].id, unprocessed.id);
        assert_eq!(containers.learning[0].id, learning.id);
        assert_eq!(containers.parked[0].id, scheduled_parked.id);
        assert_eq!(
            containers.parked[0].parked_until,
            scheduled_parked.parked_until
        );
        assert_eq!(containers.recycle_bin[0].id, recycled.id);
    }
}
