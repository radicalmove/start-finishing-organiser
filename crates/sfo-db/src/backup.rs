use chrono::Utc;
use sfo_core::{BackupManifest, TableCount};
use sqlx::FromRow;
use std::path::{Path, PathBuf};

use crate::{connect, health_check, run_migrations, DbConfig, DbError};

pub const RUST_BACKUP_TABLES: &[&str] = &["app_metadata", "projects", "tasks"];

pub async fn backup_manifest(pool: &sqlx::SqlitePool) -> Result<BackupManifest, DbError> {
    health_check(pool).await?;
    let schema =
        sqlx::query_scalar::<_, String>("SELECT value FROM app_metadata WHERE key = 'schema'")
            .fetch_one(pool)
            .await?;

    let mut tables = Vec::with_capacity(RUST_BACKUP_TABLES.len());
    for table in RUST_BACKUP_TABLES {
        tables.push(TableCount {
            table: (*table).to_string(),
            rows: count_rows(pool, table).await?,
        });
    }

    Ok(BackupManifest {
        generated_at: Utc::now(),
        database_status: "ok".to_string(),
        schema,
        tables,
    })
}

pub async fn write_backup_file(
    pool: &sqlx::SqlitePool,
    backup_dir: impl AsRef<Path>,
) -> Result<PathBuf, DbError> {
    health_check(pool).await?;
    let backup_dir = backup_dir.as_ref();
    std::fs::create_dir_all(backup_dir)?;
    let backup_path = backup_dir.join(format!(
        "sfo-rust-pre-import-{}-{}-{}.db",
        Utc::now().format("%Y%m%dT%H%M%SZ"),
        Utc::now().timestamp_nanos_opt().unwrap_or_default(),
        std::process::id()
    ));
    let backup_path_text = backup_path.to_string_lossy().to_string();
    let backup_url = format!("sqlite://{backup_path_text}");
    let backup_pool = connect(&DbConfig::new(backup_url)).await?;
    run_migrations(&backup_pool).await?;
    copy_current_tables(pool, &backup_pool).await?;
    backup_pool.close().await;

    Ok(backup_path)
}

async fn copy_current_tables(
    source_pool: &sqlx::SqlitePool,
    backup_pool: &sqlx::SqlitePool,
) -> Result<(), DbError> {
    let metadata_rows =
        sqlx::query_as::<_, BackupMetadataRow>("SELECT key, value, updated_at FROM app_metadata")
            .fetch_all(source_pool)
            .await?;
    let project_rows = sqlx::query_as::<_, BackupProjectRow>("SELECT * FROM projects")
        .fetch_all(source_pool)
        .await?;
    let task_rows = sqlx::query_as::<_, BackupTaskRow>("SELECT * FROM tasks")
        .fetch_all(source_pool)
        .await?;

    let mut transaction = backup_pool.begin().await?;
    sqlx::query("DELETE FROM tasks")
        .execute(&mut *transaction)
        .await?;
    sqlx::query("DELETE FROM projects")
        .execute(&mut *transaction)
        .await?;
    sqlx::query("DELETE FROM app_metadata")
        .execute(&mut *transaction)
        .await?;

    for row in metadata_rows {
        sqlx::query("INSERT INTO app_metadata (key, value, updated_at) VALUES (?, ?, ?)")
            .bind(row.key)
            .bind(row.value)
            .bind(row.updated_at)
            .execute(&mut *transaction)
            .await?;
    }

    for row in project_rows {
        sqlx::query(
            r#"
            INSERT INTO projects (
                id, legacy_id, title, description, category, status, size,
                time_horizon, target_date, level_of_success, why_link_text,
                active_this_week, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            "#,
        )
        .bind(row.id)
        .bind(row.legacy_id)
        .bind(row.title)
        .bind(row.description)
        .bind(row.category)
        .bind(row.status)
        .bind(row.size)
        .bind(row.time_horizon)
        .bind(row.target_date)
        .bind(row.level_of_success)
        .bind(row.why_link_text)
        .bind(row.active_this_week)
        .bind(row.created_at)
        .bind(row.updated_at)
        .execute(&mut *transaction)
        .await?;
    }

    for row in task_rows {
        sqlx::query(
            r#"
            INSERT INTO tasks (
                id, legacy_id, project_id, verb_noun, description, in_inbox,
                archived_from_inbox, intake_intent, intake_container, intake_processed_at,
                when_bucket, block_type, duration_minutes, priority, frog, alignment,
                first_action, status, scheduled_for, resurface_on, completed_at,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            "#,
        )
        .bind(row.id)
        .bind(row.legacy_id)
        .bind(row.project_id)
        .bind(row.verb_noun)
        .bind(row.description)
        .bind(row.in_inbox)
        .bind(row.archived_from_inbox)
        .bind(row.intake_intent)
        .bind(row.intake_container)
        .bind(row.intake_processed_at)
        .bind(row.when_bucket)
        .bind(row.block_type)
        .bind(row.duration_minutes)
        .bind(row.priority)
        .bind(row.frog)
        .bind(row.alignment)
        .bind(row.first_action)
        .bind(row.status)
        .bind(row.scheduled_for)
        .bind(row.resurface_on)
        .bind(row.completed_at)
        .bind(row.created_at)
        .bind(row.updated_at)
        .execute(&mut *transaction)
        .await?;
    }

    transaction.commit().await?;

    Ok(())
}

async fn count_rows(pool: &sqlx::SqlitePool, table: &str) -> Result<i64, DbError> {
    let quoted_table = quote_identifier(table);
    let query = format!("SELECT COUNT(*) FROM {quoted_table}");
    let count = sqlx::query_scalar::<_, i64>(&query).fetch_one(pool).await?;
    Ok(count)
}

fn quote_identifier(identifier: &str) -> String {
    format!("\"{}\"", identifier.replace('"', "\"\""))
}

#[derive(Debug, FromRow)]
struct BackupMetadataRow {
    key: String,
    value: String,
    updated_at: String,
}

#[derive(Debug, FromRow)]
struct BackupProjectRow {
    id: String,
    legacy_id: Option<i64>,
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

#[derive(Debug, FromRow)]
struct BackupTaskRow {
    id: String,
    legacy_id: Option<i64>,
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::planning::{create_project, create_task};
    use crate::{connect, run_migrations, DbConfig};
    use sfo_core::{ProjectCategory, ProjectCreate, TaskCreate, WhenBucket};

    #[tokio::test]
    async fn backup_manifest_reports_rust_table_counts() {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");

        create_project(
            &pool,
            ProjectCreate {
                title: "A".to_string(),
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
        .expect("create project");
        create_task(
            &pool,
            TaskCreate {
                verb_noun: "Task".to_string(),
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
        .expect("create task");

        let manifest = backup_manifest(&pool).await.expect("backup manifest");

        assert_eq!(manifest.database_status, "ok");
        assert_eq!(manifest.schema, "sfo-rust-foundation");
        assert_count(&manifest.tables, "projects", 1);
        assert_count(&manifest.tables, "tasks", 1);
        assert_count(&manifest.tables, "app_metadata", 1);
    }

    #[tokio::test]
    async fn write_backup_file_creates_sqlite_snapshot() {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        create_project(
            &pool,
            ProjectCreate {
                title: "A".to_string(),
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
        .expect("create project");
        let backup_dir = temp_dir_path("backup-file");
        std::fs::create_dir_all(&backup_dir).expect("create backup dir");

        let path = write_backup_file(&pool, &backup_dir)
            .await
            .expect("write backup file");

        assert!(path.exists());
        let backup_url = format!("sqlite://{}", path.display());
        let backup_pool = connect(&DbConfig::new(backup_url))
            .await
            .expect("connect backup");
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM projects")
            .fetch_one(&backup_pool)
            .await
            .expect("count backup projects");
        assert_eq!(count, 1);
        backup_pool.close().await;

        let _ = std::fs::remove_dir_all(backup_dir);
    }

    fn assert_count(tables: &[TableCount], name: &str, rows: i64) {
        let table = tables
            .iter()
            .find(|table| table.table == name)
            .unwrap_or_else(|| panic!("missing table {name}"));
        assert_eq!(table.rows, rows);
    }

    fn temp_dir_path(label: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "sfo-{label}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ))
    }
}
