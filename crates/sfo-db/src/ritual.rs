use chrono::{NaiveDate, Utc};
use sfo_core::{DailyFocus, DailyFocusUpdate, RitualId};
use sqlx::FromRow;

use crate::DbError;

pub async fn save_daily_focus(
    pool: &sqlx::SqlitePool,
    date: NaiveDate,
    payload: DailyFocusUpdate,
) -> Result<DailyFocus, DbError> {
    let existing_id = sqlx::query_scalar::<_, String>(
        r#"
        SELECT id
        FROM ritual_entries
        WHERE ritual_type = 'morning'
          AND entry_date = ?
        ORDER BY created_at DESC
        LIMIT 1
        "#,
    )
    .bind(date.to_string())
    .fetch_optional(pool)
    .await?;

    if let Some(id) = existing_id {
        sqlx::query(
            r#"
            UPDATE ritual_entries
            SET one_thing = ?, frog = ?, updated_at = ?
            WHERE id = ?
            "#,
        )
        .bind(trim_optional(payload.one_thing))
        .bind(trim_optional(payload.frog))
        .bind(Utc::now().to_rfc3339())
        .bind(id)
        .execute(pool)
        .await?;
    } else {
        sqlx::query(
            r#"
            INSERT INTO ritual_entries (id, ritual_type, entry_date, one_thing, frog)
            VALUES (?, 'morning', ?, ?, ?)
            "#,
        )
        .bind(RitualId::new().to_string())
        .bind(date.to_string())
        .bind(trim_optional(payload.one_thing))
        .bind(trim_optional(payload.frog))
        .execute(pool)
        .await?;
    }

    daily_focus(pool, date).await
}

pub async fn daily_focus(pool: &sqlx::SqlitePool, date: NaiveDate) -> Result<DailyFocus, DbError> {
    let row = latest_ritual_entry(pool, date, "morning").await?;
    Ok(DailyFocus {
        one_thing: row.as_ref().and_then(|entry| entry.one_thing.clone()),
        frog: row.and_then(|entry| entry.frog),
    })
}

pub async fn completed_ritual_types(
    pool: &sqlx::SqlitePool,
    date: NaiveDate,
) -> Result<Vec<String>, DbError> {
    let rows = sqlx::query_scalar::<_, String>(
        r#"
        SELECT DISTINCT ritual_type
        FROM ritual_entries
        WHERE entry_date = ?
        "#,
    )
    .bind(date.to_string())
    .fetch_all(pool)
    .await?;

    Ok(rows)
}

async fn latest_ritual_entry(
    pool: &sqlx::SqlitePool,
    date: NaiveDate,
    ritual_type: &str,
) -> Result<Option<RitualEntryRow>, DbError> {
    let row = sqlx::query_as::<_, RitualEntryRow>(
        r#"
        SELECT one_thing, frog
        FROM ritual_entries
        WHERE ritual_type = ?
          AND entry_date = ?
        ORDER BY created_at DESC
        LIMIT 1
        "#,
    )
    .bind(ritual_type)
    .bind(date.to_string())
    .fetch_optional(pool)
    .await?;

    Ok(row)
}

#[derive(Debug, FromRow)]
struct RitualEntryRow {
    one_thing: Option<String>,
    frog: Option<String>,
}

fn trim_optional(value: Option<String>) -> Option<String> {
    value
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
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
    async fn daily_focus_can_be_saved_and_loaded() {
        let pool = migrated_pool().await;
        let today = NaiveDate::from_ymd_opt(2026, 5, 6).expect("date");

        let focus = save_daily_focus(
            &pool,
            today,
            DailyFocusUpdate {
                date: Some(today),
                one_thing: Some(" Ship client shell ".to_string()),
                frog: Some("Hard call".to_string()),
            },
        )
        .await
        .expect("save focus");

        assert_eq!(focus.one_thing.as_deref(), Some("Ship client shell"));
        assert_eq!(focus.frog.as_deref(), Some("Hard call"));

        let loaded = daily_focus(&pool, today).await.expect("load focus");
        assert_eq!(loaded, focus);
        let completed = completed_ritual_types(&pool, today)
            .await
            .expect("completed rituals");
        assert_eq!(completed, vec!["morning".to_string()]);
    }
}
