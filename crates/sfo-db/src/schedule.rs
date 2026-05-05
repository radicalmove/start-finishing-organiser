use chrono::{DateTime, NaiveDate, NaiveTime, Utc};
use sfo_core::{Block, BlockCreate, BlockId, BlockUpdate, Page, TaskId};
use sqlx::FromRow;
use std::str::FromStr;

use crate::planning::{get_task, update_task};
use crate::DbError;

pub async fn create_block(pool: &sqlx::SqlitePool, payload: BlockCreate) -> Result<Block, DbError> {
    let id = BlockId::new();
    insert_block(pool, id, None, payload).await?;
    let block = get_block(pool, id)
        .await?
        .ok_or_else(|| DbError::InvalidData("created block could not be loaded".to_string()))?;
    sync_task_schedule(pool, None, &block).await?;
    Ok(block)
}

pub async fn list_blocks(
    pool: &sqlx::SqlitePool,
    page: i64,
    page_size: i64,
) -> Result<Page<Block>, DbError> {
    let page_size = normalize_page_size(page_size);
    let total: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM blocks")
        .fetch_one(pool)
        .await?;
    let page = resolve_page(page, page_size, total);
    let rows = sqlx::query_as::<_, BlockRow>(
        r#"
        SELECT * FROM blocks
        ORDER BY date ASC, start_time IS NULL ASC, start_time ASC, created_at ASC
        LIMIT ? OFFSET ?
        "#,
    )
    .bind(page_size)
    .bind((page - 1) * page_size)
    .fetch_all(pool)
    .await?;
    let items = rows
        .into_iter()
        .map(Block::try_from)
        .collect::<Result<Vec<_>, _>>()?;

    Ok(Page::new(items, page, page_size, total))
}

pub async fn get_block(pool: &sqlx::SqlitePool, id: BlockId) -> Result<Option<Block>, DbError> {
    let row = sqlx::query_as::<_, BlockRow>("SELECT * FROM blocks WHERE id = ?")
        .bind(id.to_string())
        .fetch_optional(pool)
        .await?;

    row.map(Block::try_from).transpose()
}

pub async fn update_block(
    pool: &sqlx::SqlitePool,
    id: BlockId,
    payload: BlockUpdate,
) -> Result<Block, DbError> {
    let previous = get_block(pool, id)
        .await?
        .ok_or_else(|| DbError::InvalidData("block not found".to_string()))?;
    let mut block = previous.clone();

    if let Some(title) = payload.title {
        block.title = normalize_optional_text(title);
    }
    if let Some(date) = payload.date {
        block.date = date;
    }
    if let Some(start_time) = payload.start_time {
        block.start_time = start_time;
    }
    if let Some(end_time) = payload.end_time {
        block.end_time = end_time;
    }
    if let Some(block_type) = payload.block_type {
        block.block_type = block_type;
    }
    if let Some(project_id) = payload.project_id {
        block.project_id = project_id;
    }
    if let Some(task_id) = payload.task_id {
        block.task_id = task_id;
    }
    if let Some(notes) = payload.notes {
        block.notes = normalize_optional_text(notes);
    }

    sqlx::query(
        r#"
        UPDATE blocks
        SET title = ?, date = ?, start_time = ?, end_time = ?, block_type = ?,
            project_id = ?, task_id = ?, notes = ?, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(&block.title)
    .bind(format_date(block.date))
    .bind(format_time(block.start_time))
    .bind(format_time(block.end_time))
    .bind(block.block_type.as_str())
    .bind(block.project_id.map(|value| value.to_string()))
    .bind(block.task_id.map(|value| value.to_string()))
    .bind(&block.notes)
    .bind(now_text())
    .bind(id.to_string())
    .execute(pool)
    .await?;

    let updated = get_block(pool, id)
        .await?
        .ok_or_else(|| DbError::InvalidData("updated block could not be loaded".to_string()))?;
    sync_task_schedule(pool, Some(&previous), &updated).await?;
    Ok(updated)
}

pub async fn delete_block(pool: &sqlx::SqlitePool, id: BlockId) -> Result<bool, DbError> {
    let previous = get_block(pool, id).await?;
    let result = sqlx::query("DELETE FROM blocks WHERE id = ?")
        .bind(id.to_string())
        .execute(pool)
        .await?;

    if result.rows_affected() > 0 {
        if let Some(block) = previous {
            clear_task_schedule(pool, block.task_id).await?;
        }
        Ok(true)
    } else {
        Ok(false)
    }
}

pub async fn insert_imported_block(
    pool: &sqlx::SqlitePool,
    legacy_id: i64,
    payload: BlockCreate,
    created_at: String,
) -> Result<u64, DbError> {
    let id = BlockId::new();
    let result = sqlx::query(
        r#"
        INSERT INTO blocks (
            id, legacy_id, title, date, start_time, end_time, block_type,
            project_id, task_id, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(legacy_id) DO UPDATE SET
            title = excluded.title,
            date = excluded.date,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            block_type = excluded.block_type,
            project_id = excluded.project_id,
            task_id = excluded.task_id,
            notes = excluded.notes,
            created_at = excluded.created_at
        "#,
    )
    .bind(id.to_string())
    .bind(legacy_id)
    .bind(normalize_optional_text(payload.title))
    .bind(format_date(payload.date))
    .bind(format_time(payload.start_time))
    .bind(format_time(payload.end_time))
    .bind(payload.block_type.as_str())
    .bind(payload.project_id.map(|value| value.to_string()))
    .bind(payload.task_id.map(|value| value.to_string()))
    .bind(normalize_optional_text(payload.notes))
    .bind(created_at)
    .execute(pool)
    .await?;

    Ok(result.rows_affected())
}

async fn insert_block(
    pool: &sqlx::SqlitePool,
    id: BlockId,
    legacy_id: Option<i64>,
    payload: BlockCreate,
) -> Result<(), DbError> {
    sqlx::query(
        r#"
        INSERT INTO blocks (
            id, legacy_id, title, date, start_time, end_time, block_type,
            project_id, task_id, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
    .bind(id.to_string())
    .bind(legacy_id)
    .bind(normalize_optional_text(payload.title))
    .bind(format_date(payload.date))
    .bind(format_time(payload.start_time))
    .bind(format_time(payload.end_time))
    .bind(payload.block_type.as_str())
    .bind(payload.project_id.map(|value| value.to_string()))
    .bind(payload.task_id.map(|value| value.to_string()))
    .bind(normalize_optional_text(payload.notes))
    .execute(pool)
    .await?;

    Ok(())
}

async fn sync_task_schedule(
    pool: &sqlx::SqlitePool,
    previous: Option<&Block>,
    current: &Block,
) -> Result<(), DbError> {
    if previous.and_then(|block| block.task_id) != current.task_id {
        if let Some(block) = previous {
            clear_task_schedule(pool, block.task_id).await?;
        }
    }

    if let Some(task_id) = current.task_id {
        let mut task = get_task(pool, task_id).await?.ok_or_else(|| {
            DbError::InvalidData("scheduled task could not be loaded".to_string())
        })?;
        task.scheduled_for = Some(current.date);
        update_task(pool, &task).await?;
    }

    Ok(())
}

async fn clear_task_schedule(
    pool: &sqlx::SqlitePool,
    task_id: Option<TaskId>,
) -> Result<(), DbError> {
    if let Some(task_id) = task_id {
        if let Some(mut task) = get_task(pool, task_id).await? {
            task.scheduled_for = None;
            update_task(pool, &task).await?;
        }
    }
    Ok(())
}

#[derive(Debug, FromRow)]
pub(crate) struct BlockRow {
    id: String,
    title: Option<String>,
    date: String,
    start_time: Option<String>,
    end_time: Option<String>,
    block_type: String,
    project_id: Option<String>,
    task_id: Option<String>,
    notes: Option<String>,
    created_at: String,
    updated_at: Option<String>,
}

impl TryFrom<BlockRow> for Block {
    type Error = DbError;

    fn try_from(row: BlockRow) -> Result<Self, Self::Error> {
        Ok(Self {
            id: parse_id(&row.id)?,
            title: row.title,
            date: parse_date(&row.date)?,
            start_time: parse_optional_time(row.start_time)?,
            end_time: parse_optional_time(row.end_time)?,
            block_type: parse_enum(&row.block_type)?,
            project_id: parse_optional_id(row.project_id)?,
            task_id: parse_optional_id(row.task_id)?,
            notes: row.notes,
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

fn normalize_optional_text(value: Option<String>) -> Option<String> {
    value.and_then(|text| {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(trimmed.to_string())
        }
    })
}

fn now_text() -> String {
    Utc::now().to_rfc3339()
}

fn format_date(value: NaiveDate) -> String {
    value.to_string()
}

fn format_time(value: Option<NaiveTime>) -> Option<String> {
    value.map(|time| time.format("%H:%M:%S").to_string())
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

fn parse_date(value: &str) -> Result<NaiveDate, DbError> {
    NaiveDate::parse_from_str(value, "%Y-%m-%d")
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_optional_time(value: Option<String>) -> Result<Option<NaiveTime>, DbError> {
    value
        .as_deref()
        .map(|time| {
            NaiveTime::parse_from_str(time, "%H:%M:%S")
                .or_else(|_| NaiveTime::parse_from_str(time, "%H:%M"))
                .map_err(|error| DbError::InvalidData(error.to_string()))
        })
        .transpose()
}

fn parse_datetime(value: &str) -> Result<DateTime<Utc>, DbError> {
    DateTime::parse_from_rfc3339(value)
        .map(|date_time| date_time.with_timezone(&Utc))
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_optional_datetime(value: Option<String>) -> Result<Option<DateTime<Utc>>, DbError> {
    value.as_deref().map(parse_datetime).transpose()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::planning::{create_project, create_task, get_task};
    use crate::{connect, run_migrations, DbConfig};
    use chrono::{NaiveDate, NaiveTime};
    use sfo_core::{
        BlockCreate, BlockType, BlockUpdate, ProjectCategory, ProjectCreate, TaskCreate, WhenBucket,
    };

    async fn migrated_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn blocks_can_be_inserted_listed_updated_and_deleted() {
        let pool = migrated_pool().await;
        let project = create_project(
            &pool,
            ProjectCreate {
                title: "Project".to_string(),
                description: None,
                category: ProjectCategory::Work,
                size: None,
                time_horizon: None,
                target_date: None,
                level_of_success: None,
                why_link_text: None,
                active_this_week: false,
            },
        )
        .await
        .expect("project");
        let task = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Write block tests".to_string(),
                project_id: Some(project.id),
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Today,
                block_type: Some(BlockType::Focus),
                duration_minutes: Some(45),
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            },
        )
        .await
        .expect("task");

        let block = create_block(
            &pool,
            BlockCreate {
                title: Some("Focus block".to_string()),
                date: NaiveDate::from_ymd_opt(2026, 5, 6).expect("date"),
                start_time: Some(NaiveTime::from_hms_opt(9, 0, 0).expect("start")),
                end_time: Some(NaiveTime::from_hms_opt(9, 45, 0).expect("end")),
                block_type: BlockType::Focus,
                project_id: Some(project.id),
                task_id: Some(task.id),
                notes: Some("Close Slack".to_string()),
            },
        )
        .await
        .expect("create block");

        assert_eq!(block.title.as_deref(), Some("Focus block"));
        assert_eq!(block.project_id, Some(project.id));
        assert_eq!(block.task_id, Some(task.id));

        let page = list_blocks(&pool, 1, 10).await.expect("list blocks");
        assert_eq!(page.total, 1);
        assert_eq!(page.items[0].id, block.id);

        let updated = update_block(
            &pool,
            block.id,
            BlockUpdate {
                title: Some(Some("Renamed block".to_string())),
                notes: Some(None),
                ..Default::default()
            },
        )
        .await
        .expect("update block");
        assert_eq!(updated.title.as_deref(), Some("Renamed block"));
        assert_eq!(updated.notes, None);

        assert!(delete_block(&pool, updated.id).await.expect("delete block"));
        assert!(get_block(&pool, updated.id)
            .await
            .expect("get deleted block")
            .is_none());
    }

    #[tokio::test]
    async fn deleting_task_block_clears_task_schedule_date() {
        let pool = migrated_pool().await;
        let task = create_task(
            &pool,
            TaskCreate {
                verb_noun: "Schedule me".to_string(),
                project_id: None,
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Today,
                block_type: Some(BlockType::Admin),
                duration_minutes: Some(30),
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            },
        )
        .await
        .expect("task");
        let block_date = NaiveDate::from_ymd_opt(2026, 5, 6).expect("date");
        let block = create_block(
            &pool,
            BlockCreate {
                title: Some("Admin".to_string()),
                date: block_date,
                start_time: None,
                end_time: None,
                block_type: BlockType::Admin,
                project_id: None,
                task_id: Some(task.id),
                notes: None,
            },
        )
        .await
        .expect("create block");

        let scheduled = get_task(&pool, task.id)
            .await
            .expect("get task")
            .expect("task exists");
        assert_eq!(scheduled.scheduled_for, Some(block_date));

        delete_block(&pool, block.id).await.expect("delete block");

        let unscheduled = get_task(&pool, task.id)
            .await
            .expect("get task")
            .expect("task exists");
        assert_eq!(unscheduled.scheduled_for, None);
    }
}
