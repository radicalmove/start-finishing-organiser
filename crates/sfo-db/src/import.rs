use sfo_core::{ImportDryRunReport, TableImportSummary};
use sha2::{Digest, Sha256};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions};
use std::collections::HashSet;
use std::path::Path;
use std::str::FromStr;

use crate::DbError;

pub const SUPPORTED_PYTHON_TABLES: &[&str] = &["projects", "tasks"];
pub const KNOWN_PYTHON_TABLES: &[&str] = &[
    "projects",
    "tasks",
    "blocks",
    "success_packs",
    "waiting_on",
    "ritual_entries",
    "profiles",
    "health_metrics",
    "health_entries",
    "health_goals",
    "health_supplements",
    "health_exercise_sessions",
    "health_training_plans",
    "health_training_set_logs",
    "coach_conversations",
    "coach_messages",
    "guidance_reminders",
    "guidance_events",
    "email_sync_state",
    "email_messages",
];

pub async fn dry_run_python_sqlite_import(
    source_path: impl AsRef<Path>,
) -> Result<ImportDryRunReport, DbError> {
    let source_path = source_path.as_ref();
    let source_sha256 = file_sha256(source_path)?;
    let source_path_text = source_path.to_string_lossy().to_string();
    let url = format!("sqlite://{source_path_text}");
    let options = SqliteConnectOptions::from_str(&url)?
        .read_only(true)
        .create_if_missing(false);
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect_with(options)
        .await?;

    let table_names = source_table_names(&pool).await?;
    let supported_tables: HashSet<&'static str> = SUPPORTED_PYTHON_TABLES.iter().copied().collect();
    let known_tables: HashSet<&'static str> = KNOWN_PYTHON_TABLES.iter().copied().collect();
    let mut tables = Vec::with_capacity(table_names.len());
    let mut warnings = Vec::new();

    for table in &table_names {
        let rows = count_rows(&pool, table).await?;
        let supported = supported_tables.contains(table.as_str());
        if !supported {
            warnings.push(format!("table {table} is not imported in this slice"));
        }
        tables.push(TableImportSummary {
            table: table.clone(),
            rows,
            supported,
        });
    }

    for known_table in KNOWN_PYTHON_TABLES {
        if !table_names.iter().any(|table| table == known_table) {
            warnings.push(format!("missing known table {known_table}"));
        }
    }

    for table in &table_names {
        if !known_tables.contains(table.as_str()) {
            warnings.push(format!("unknown source table {table}"));
        }
    }

    pool.close().await;

    Ok(ImportDryRunReport {
        source_path: source_path_text,
        source_sha256,
        tables,
        warnings,
    })
}

async fn source_table_names(pool: &sqlx::SqlitePool) -> Result<Vec<String>, DbError> {
    let tables = sqlx::query_scalar::<_, String>(
        r#"
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
          AND name != '_sqlx_migrations'
        ORDER BY name ASC
        "#,
    )
    .fetch_all(pool)
    .await?;

    Ok(tables)
}

async fn count_rows(pool: &sqlx::SqlitePool, table: &str) -> Result<i64, DbError> {
    let quoted_table = quote_identifier(table);
    let query = format!("SELECT COUNT(*) FROM {quoted_table}");
    let count = sqlx::query_scalar::<_, i64>(&query).fetch_one(pool).await?;
    Ok(count)
}

fn file_sha256(path: &Path) -> Result<String, DbError> {
    let bytes = std::fs::read(path)?;
    let digest = Sha256::digest(bytes);
    Ok(format!("{digest:x}"))
}

fn quote_identifier(identifier: &str) -> String {
    format!("\"{}\"", identifier.replace('"', "\"\""))
}

#[cfg(test)]
mod tests {
    use super::*;
    use sqlx::sqlite::SqliteConnectOptions;
    use std::str::FromStr;

    #[tokio::test]
    async fn dry_run_reports_supported_and_unsupported_python_tables() {
        let path = temp_db_path("python-source");
        create_python_fixture(&path).await;

        let report = dry_run_python_sqlite_import(&path)
            .await
            .expect("dry-run import");

        assert_eq!(report.source_path, path.to_string_lossy());
        assert_eq!(report.source_sha256.len(), 64);
        assert_table(&report.tables, "projects", 2, true);
        assert_table(&report.tables, "tasks", 3, true);
        assert_table(&report.tables, "health_entries", 1, false);
        assert!(report
            .warnings
            .iter()
            .any(|warning| warning.contains("health_entries")));
        assert!(report
            .warnings
            .iter()
            .any(|warning| warning.contains("missing known table blocks")));

        let _ = std::fs::remove_file(path);
    }

    fn assert_table(tables: &[TableImportSummary], name: &str, rows: i64, supported: bool) {
        let table = tables
            .iter()
            .find(|table| table.table == name)
            .unwrap_or_else(|| panic!("missing table {name}"));

        assert_eq!(table.rows, rows);
        assert_eq!(table.supported, supported);
    }

    async fn create_python_fixture(path: &std::path::Path) {
        let url = format!("sqlite://{}", path.display());
        let options = SqliteConnectOptions::from_str(&url)
            .expect("sqlite options")
            .create_if_missing(true);
        let pool = sqlx::SqlitePool::connect_with(options)
            .await
            .expect("fixture connection");

        sqlx::query("CREATE TABLE projects (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
            .execute(&pool)
            .await
            .expect("create projects");
        sqlx::query("INSERT INTO projects (title) VALUES ('A'), ('B')")
            .execute(&pool)
            .await
            .expect("insert projects");

        sqlx::query("CREATE TABLE tasks (id INTEGER PRIMARY KEY, verb_noun TEXT NOT NULL)")
            .execute(&pool)
            .await
            .expect("create tasks");
        sqlx::query("INSERT INTO tasks (verb_noun) VALUES ('A'), ('B'), ('C')")
            .execute(&pool)
            .await
            .expect("insert tasks");

        sqlx::query("CREATE TABLE health_entries (id INTEGER PRIMARY KEY, value REAL NOT NULL)")
            .execute(&pool)
            .await
            .expect("create health entries");
        sqlx::query("INSERT INTO health_entries (value) VALUES (1.0)")
            .execute(&pool)
            .await
            .expect("insert health entry");

        pool.close().await;
    }

    fn temp_db_path(label: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "sfo-{label}-{}-{}.db",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ))
    }
}
