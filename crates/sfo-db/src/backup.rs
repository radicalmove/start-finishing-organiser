use chrono::Utc;
use sfo_core::{BackupManifest, TableCount};

use crate::{health_check, DbError};

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

async fn count_rows(pool: &sqlx::SqlitePool, table: &str) -> Result<i64, DbError> {
    let quoted_table = quote_identifier(table);
    let query = format!("SELECT COUNT(*) FROM {quoted_table}");
    let count = sqlx::query_scalar::<_, i64>(&query).fetch_one(pool).await?;
    Ok(count)
}

fn quote_identifier(identifier: &str) -> String {
    format!("\"{}\"", identifier.replace('"', "\"\""))
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

    fn assert_count(tables: &[TableCount], name: &str, rows: i64) {
        let table = tables
            .iter()
            .find(|table| table.table == name)
            .unwrap_or_else(|| panic!("missing table {name}"));
        assert_eq!(table.rows, rows);
    }
}
