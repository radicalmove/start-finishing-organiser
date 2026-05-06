use chrono::{DateTime, NaiveDate, Utc};
use sfo_core::{Page, WaitingId, WaitingOn, WaitingOnCreate};
use sqlx::FromRow;
use std::str::FromStr;

use crate::DbError;

pub async fn create_waiting_on(
    pool: &sqlx::SqlitePool,
    payload: WaitingOnCreate,
) -> Result<WaitingOn, DbError> {
    let id = WaitingId::new();
    sqlx::query(
        r#"
        INSERT INTO waiting_on (id, project_id, description, person, last_followup)
        VALUES (?, ?, ?, ?, ?)
        "#,
    )
    .bind(id.to_string())
    .bind(payload.project_id.map(|value| value.to_string()))
    .bind(payload.description)
    .bind(payload.person)
    .bind(format_date(payload.last_followup))
    .execute(pool)
    .await?;

    get_waiting_on(pool, id)
        .await?
        .ok_or_else(|| DbError::InvalidData("created waiting item could not be loaded".to_string()))
}

pub async fn list_waiting_on(
    pool: &sqlx::SqlitePool,
    page: i64,
    page_size: i64,
) -> Result<Page<WaitingOn>, DbError> {
    let page_size = normalize_page_size(page_size);
    let total: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM waiting_on")
        .fetch_one(pool)
        .await?;
    let page = resolve_page(page, page_size, total);
    let rows = sqlx::query_as::<_, WaitingOnRow>(
        r#"
        SELECT * FROM waiting_on
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
        .map(WaitingOn::try_from)
        .collect::<Result<Vec<_>, _>>()?;

    Ok(Page::new(items, page, page_size, total))
}

pub async fn get_waiting_on(
    pool: &sqlx::SqlitePool,
    id: WaitingId,
) -> Result<Option<WaitingOn>, DbError> {
    let row = sqlx::query_as::<_, WaitingOnRow>("SELECT * FROM waiting_on WHERE id = ?")
        .bind(id.to_string())
        .fetch_optional(pool)
        .await?;

    row.map(WaitingOn::try_from).transpose()
}

pub async fn update_waiting_on(
    pool: &sqlx::SqlitePool,
    item: &WaitingOn,
) -> Result<WaitingOn, DbError> {
    sqlx::query(
        r#"
        UPDATE waiting_on
        SET project_id = ?, description = ?, person = ?, last_followup = ?, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(item.project_id.map(|value| value.to_string()))
    .bind(&item.description)
    .bind(&item.person)
    .bind(format_date(item.last_followup))
    .bind(Utc::now().to_rfc3339())
    .bind(item.id.to_string())
    .execute(pool)
    .await?;

    get_waiting_on(pool, item.id)
        .await?
        .ok_or_else(|| DbError::InvalidData("updated waiting item could not be loaded".to_string()))
}

pub async fn delete_waiting_on(pool: &sqlx::SqlitePool, id: WaitingId) -> Result<bool, DbError> {
    let result = sqlx::query("DELETE FROM waiting_on WHERE id = ?")
        .bind(id.to_string())
        .execute(pool)
        .await?;

    Ok(result.rows_affected() > 0)
}

#[derive(Debug, FromRow)]
pub(crate) struct WaitingOnRow {
    id: String,
    project_id: Option<String>,
    description: String,
    person: Option<String>,
    last_followup: Option<String>,
    created_at: String,
    updated_at: Option<String>,
}

impl TryFrom<WaitingOnRow> for WaitingOn {
    type Error = DbError;

    fn try_from(row: WaitingOnRow) -> Result<Self, Self::Error> {
        Ok(Self {
            id: parse_id(&row.id)?,
            project_id: parse_optional_id(row.project_id)?,
            description: row.description,
            person: row.person,
            last_followup: parse_optional_date(row.last_followup)?,
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

    async fn migrated_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn waiting_on_items_can_be_inserted_listed_updated_and_deleted() {
        let pool = migrated_pool().await;
        let item = create_waiting_on(
            &pool,
            WaitingOnCreate {
                description: "Waiting on Sam".to_string(),
                person: Some("Sam".to_string()),
                project_id: None,
                last_followup: Some(NaiveDate::from_ymd_opt(2026, 5, 10).expect("date")),
            },
        )
        .await
        .expect("create waiting");

        assert_eq!(item.person.as_deref(), Some("Sam"));
        let page = list_waiting_on(&pool, 1, 10).await.expect("list waiting");
        assert_eq!(page.total, 1);

        let mut updated = item;
        updated.person = Some("Alex".to_string());
        updated.last_followup = None;
        let updated = update_waiting_on(&pool, &updated)
            .await
            .expect("update waiting");
        assert_eq!(updated.person.as_deref(), Some("Alex"));
        assert!(updated.last_followup.is_none());

        assert!(delete_waiting_on(&pool, updated.id)
            .await
            .expect("delete waiting"));
    }
}
