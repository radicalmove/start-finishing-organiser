use chrono::{DateTime, NaiveDateTime, Utc};
use sfo_core::{
    ImportDryRunReport, ProjectId, PythonSqliteImportReport, TableImportResult, TableImportSummary,
    TaskId, WaitingId, INBOX_INTENT_UNPROCESSED,
};
use sha2::{Digest, Sha256};
use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions};
use sqlx::FromRow;
use std::collections::HashSet;
use std::path::Path;
use std::str::FromStr;

use crate::{backup::write_backup_file, DbError};

pub const SUPPORTED_PYTHON_TABLES: &[&str] = &["projects", "tasks", "blocks", "waiting_on"];
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

pub async fn import_python_sqlite(
    target_pool: &sqlx::SqlitePool,
    source_path: impl AsRef<Path>,
    backup_dir: impl AsRef<Path>,
) -> Result<PythonSqliteImportReport, DbError> {
    let source_path = source_path.as_ref();
    let source_sha256 = file_sha256(source_path)?;
    let source_path_text = source_path.to_string_lossy().to_string();
    let source_pool = open_source_pool(source_path).await?;
    let table_names = source_table_names(&source_pool).await?;
    let mut warnings = unsupported_table_warnings(&table_names);

    let backup_path = write_backup_file(target_pool, backup_dir).await?;

    let mut transaction = target_pool.begin().await?;
    let mut tables = Vec::new();

    if table_names.iter().any(|table| table == "projects") {
        let (source_rows, imported_rows) = import_projects(&source_pool, &mut transaction).await?;
        tables.push(TableImportResult {
            table: "projects".to_string(),
            source_rows,
            imported_rows,
        });
    } else {
        warnings.push("missing source table projects".to_string());
        tables.push(TableImportResult {
            table: "projects".to_string(),
            source_rows: 0,
            imported_rows: 0,
        });
    }

    if table_names.iter().any(|table| table == "tasks") {
        let (source_rows, imported_rows, task_warnings) =
            import_tasks(&source_pool, &mut transaction).await?;
        warnings.extend(task_warnings);
        tables.push(TableImportResult {
            table: "tasks".to_string(),
            source_rows,
            imported_rows,
        });
    } else {
        warnings.push("missing source table tasks".to_string());
        tables.push(TableImportResult {
            table: "tasks".to_string(),
            source_rows: 0,
            imported_rows: 0,
        });
    }

    if table_names.iter().any(|table| table == "waiting_on") {
        let (source_rows, imported_rows, waiting_warnings) =
            import_waiting_on(&source_pool, &mut transaction).await?;
        warnings.extend(waiting_warnings);
        tables.push(TableImportResult {
            table: "waiting_on".to_string(),
            source_rows,
            imported_rows,
        });
    } else {
        warnings.push("missing source table waiting_on".to_string());
        tables.push(TableImportResult {
            table: "waiting_on".to_string(),
            source_rows: 0,
            imported_rows: 0,
        });
    }

    if table_names.iter().any(|table| table == "blocks") {
        let (source_rows, imported_rows, block_warnings) =
            import_blocks(&source_pool, &mut transaction).await?;
        warnings.extend(block_warnings);
        tables.push(TableImportResult {
            table: "blocks".to_string(),
            source_rows,
            imported_rows,
        });
    } else {
        warnings.push("missing source table blocks".to_string());
        tables.push(TableImportResult {
            table: "blocks".to_string(),
            source_rows: 0,
            imported_rows: 0,
        });
    }

    transaction.commit().await?;
    source_pool.close().await;

    Ok(PythonSqliteImportReport {
        source_path: source_path_text,
        source_sha256,
        backup_path: backup_path.to_string_lossy().to_string(),
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

async fn open_source_pool(source_path: &Path) -> Result<sqlx::SqlitePool, DbError> {
    let source_path_text = source_path.to_string_lossy().to_string();
    let url = format!("sqlite://{source_path_text}");
    let options = SqliteConnectOptions::from_str(&url)?
        .read_only(true)
        .create_if_missing(false);
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect_with(options)
        .await?;
    Ok(pool)
}

async fn count_rows(pool: &sqlx::SqlitePool, table: &str) -> Result<i64, DbError> {
    let quoted_table = quote_identifier(table);
    let query = format!("SELECT COUNT(*) FROM {quoted_table}");
    let count = sqlx::query_scalar::<_, i64>(&query).fetch_one(pool).await?;
    Ok(count)
}

async fn import_projects(
    source_pool: &sqlx::SqlitePool,
    transaction: &mut sqlx::Transaction<'_, sqlx::Sqlite>,
) -> Result<(i64, i64), DbError> {
    let rows = sqlx::query_as::<_, LegacyProjectRow>(
        r#"
        SELECT id, title, description, category, status, size, time_horizon,
               target_date, level_of_success, why_link_text, active_this_week,
               created_at, updated_at
        FROM projects
        ORDER BY id ASC
        "#,
    )
    .fetch_all(source_pool)
    .await?;
    let source_rows =
        i64::try_from(rows.len()).map_err(|error| DbError::InvalidData(error.to_string()))?;
    let mut imported_rows = 0;

    for row in rows {
        let rust_id = ProjectId::new().to_string();
        let created_at = normalize_required_datetime(row.created_at)?;
        let updated_at = normalize_optional_datetime(row.updated_at)?;

        let result = sqlx::query(
            r#"
            INSERT INTO projects (
                id, legacy_id, title, description, category, status, size,
                time_horizon, target_date, level_of_success, why_link_text,
                active_this_week, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(legacy_id) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                category = excluded.category,
                status = excluded.status,
                size = excluded.size,
                time_horizon = excluded.time_horizon,
                target_date = excluded.target_date,
                level_of_success = excluded.level_of_success,
                why_link_text = excluded.why_link_text,
                active_this_week = excluded.active_this_week,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
            "#,
        )
        .bind(rust_id)
        .bind(row.id)
        .bind(row.title)
        .bind(optional_text(row.description))
        .bind(default_text(row.category, "work"))
        .bind(default_text(row.status, "active"))
        .bind(optional_text(row.size))
        .bind(optional_text(row.time_horizon))
        .bind(optional_text(row.target_date))
        .bind(optional_text(row.level_of_success))
        .bind(optional_text(row.why_link_text))
        .bind(row.active_this_week)
        .bind(created_at)
        .bind(updated_at)
        .execute(&mut **transaction)
        .await?;
        imported_rows += i64::try_from(result.rows_affected())
            .map_err(|error| DbError::InvalidData(error.to_string()))?;
    }

    Ok((source_rows, imported_rows))
}

async fn import_tasks(
    source_pool: &sqlx::SqlitePool,
    transaction: &mut sqlx::Transaction<'_, sqlx::Sqlite>,
) -> Result<(i64, i64, Vec<String>), DbError> {
    let rows = sqlx::query_as::<_, LegacyTaskRow>(
        r#"
        SELECT id, project_id, verb_noun, description, in_inbox, archived_from_inbox,
               intake_intent, intake_container, intake_processed_at, when_bucket,
               block_type, duration_minutes, priority, frog, alignment, first_action,
               status, scheduled_for, owner_type, resurface_on, completed_at, created_at
        FROM tasks
        ORDER BY id ASC
        "#,
    )
    .fetch_all(source_pool)
    .await?;
    let source_rows =
        i64::try_from(rows.len()).map_err(|error| DbError::InvalidData(error.to_string()))?;
    let mut imported_rows = 0;
    let mut warnings = Vec::new();

    for row in rows {
        let rust_id = TaskId::new().to_string();
        let project_id = match row.project_id {
            Some(legacy_project_id) => {
                let mapped_project_id: Option<String> =
                    sqlx::query_scalar("SELECT id FROM projects WHERE legacy_id = ?")
                        .bind(legacy_project_id)
                        .fetch_optional(&mut **transaction)
                        .await?;
                if mapped_project_id.is_none() {
                    warnings.push(format!(
                        "task {} references missing project {}",
                        row.id, legacy_project_id
                    ));
                }
                mapped_project_id
            }
            None => None,
        };
        let intake_processed_at = normalize_optional_datetime(row.intake_processed_at)?;
        let completed_at = normalize_optional_datetime(row.completed_at)?;
        let created_at = normalize_required_datetime(row.created_at)?;

        let result = sqlx::query(
            r#"
            INSERT INTO tasks (
                id, legacy_id, project_id, verb_noun, description, in_inbox,
                archived_from_inbox, intake_intent, intake_container, intake_processed_at,
                when_bucket, block_type, duration_minutes, priority, frog, alignment,
                first_action, status, scheduled_for, owner_type, resurface_on, completed_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(legacy_id) DO UPDATE SET
                project_id = excluded.project_id,
                verb_noun = excluded.verb_noun,
                description = excluded.description,
                in_inbox = excluded.in_inbox,
                archived_from_inbox = excluded.archived_from_inbox,
                intake_intent = excluded.intake_intent,
                intake_container = excluded.intake_container,
                intake_processed_at = excluded.intake_processed_at,
                when_bucket = excluded.when_bucket,
                block_type = excluded.block_type,
                duration_minutes = excluded.duration_minutes,
                priority = excluded.priority,
                frog = excluded.frog,
                alignment = excluded.alignment,
                first_action = excluded.first_action,
                status = excluded.status,
                scheduled_for = excluded.scheduled_for,
                owner_type = excluded.owner_type,
                resurface_on = excluded.resurface_on,
                completed_at = excluded.completed_at,
                created_at = excluded.created_at
            "#,
        )
        .bind(rust_id)
        .bind(row.id)
        .bind(project_id)
        .bind(row.verb_noun)
        .bind(optional_text(row.description))
        .bind(row.in_inbox)
        .bind(row.archived_from_inbox)
        .bind(default_text(row.intake_intent, INBOX_INTENT_UNPROCESSED))
        .bind(default_text(row.intake_container, INBOX_INTENT_UNPROCESSED))
        .bind(intake_processed_at)
        .bind(default_text(row.when_bucket, "later"))
        .bind(optional_text(row.block_type))
        .bind(row.duration_minutes)
        .bind(row.priority)
        .bind(row.frog)
        .bind(optional_text(row.alignment))
        .bind(optional_text(row.first_action))
        .bind(default_text(row.status, "pending"))
        .bind(optional_text(row.scheduled_for))
        .bind(default_text(row.owner_type, "mine"))
        .bind(optional_text(row.resurface_on))
        .bind(completed_at)
        .bind(created_at)
        .execute(&mut **transaction)
        .await?;
        imported_rows += i64::try_from(result.rows_affected())
            .map_err(|error| DbError::InvalidData(error.to_string()))?;
    }

    Ok((source_rows, imported_rows, warnings))
}

async fn import_blocks(
    source_pool: &sqlx::SqlitePool,
    transaction: &mut sqlx::Transaction<'_, sqlx::Sqlite>,
) -> Result<(i64, i64, Vec<String>), DbError> {
    let rows = sqlx::query_as::<_, LegacyBlockRow>(
        r#"
        SELECT id, title, date, start_time, end_time, block_type,
               project_id, task_id, notes, created_at
        FROM blocks
        ORDER BY id ASC
        "#,
    )
    .fetch_all(source_pool)
    .await?;
    let source_rows =
        i64::try_from(rows.len()).map_err(|error| DbError::InvalidData(error.to_string()))?;
    let mut imported_rows = 0;
    let mut warnings = Vec::new();

    for row in rows {
        let rust_id = sfo_core::BlockId::new().to_string();
        let project_id = match row.project_id {
            Some(legacy_project_id) => {
                let mapped_project_id: Option<String> =
                    sqlx::query_scalar("SELECT id FROM projects WHERE legacy_id = ?")
                        .bind(legacy_project_id)
                        .fetch_optional(&mut **transaction)
                        .await?;
                if mapped_project_id.is_none() {
                    warnings.push(format!(
                        "block {} references missing project {}",
                        row.id, legacy_project_id
                    ));
                }
                mapped_project_id
            }
            None => None,
        };
        let task_id = match row.task_id {
            Some(legacy_task_id) => {
                let mapped_task_id: Option<String> =
                    sqlx::query_scalar("SELECT id FROM tasks WHERE legacy_id = ?")
                        .bind(legacy_task_id)
                        .fetch_optional(&mut **transaction)
                        .await?;
                if mapped_task_id.is_none() {
                    warnings.push(format!(
                        "block {} references missing task {}",
                        row.id, legacy_task_id
                    ));
                }
                mapped_task_id
            }
            None => None,
        };
        let created_at = normalize_required_datetime(row.created_at)?;

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
        .bind(rust_id)
        .bind(row.id)
        .bind(optional_text(row.title))
        .bind(normalize_required_date(row.date)?)
        .bind(normalize_optional_time(row.start_time)?)
        .bind(normalize_optional_time(row.end_time)?)
        .bind(default_text(row.block_type, "focus"))
        .bind(project_id)
        .bind(task_id)
        .bind(optional_text(row.notes))
        .bind(created_at)
        .execute(&mut **transaction)
        .await?;
        imported_rows += i64::try_from(result.rows_affected())
            .map_err(|error| DbError::InvalidData(error.to_string()))?;
    }

    Ok((source_rows, imported_rows, warnings))
}

async fn import_waiting_on(
    source_pool: &sqlx::SqlitePool,
    transaction: &mut sqlx::Transaction<'_, sqlx::Sqlite>,
) -> Result<(i64, i64, Vec<String>), DbError> {
    let rows = sqlx::query_as::<_, LegacyWaitingOnRow>(
        r#"
        SELECT id, project_id, description, person, created_at, last_followup
        FROM waiting_on
        ORDER BY id ASC
        "#,
    )
    .fetch_all(source_pool)
    .await?;
    let source_rows =
        i64::try_from(rows.len()).map_err(|error| DbError::InvalidData(error.to_string()))?;
    let mut imported_rows = 0;
    let mut warnings = Vec::new();

    for row in rows {
        let rust_id = WaitingId::new().to_string();
        let project_id = match row.project_id {
            Some(legacy_project_id) => {
                let mapped_project_id: Option<String> =
                    sqlx::query_scalar("SELECT id FROM projects WHERE legacy_id = ?")
                        .bind(legacy_project_id)
                        .fetch_optional(&mut **transaction)
                        .await?;
                if mapped_project_id.is_none() {
                    warnings.push(format!(
                        "waiting item {} references missing project {}",
                        row.id, legacy_project_id
                    ));
                }
                mapped_project_id
            }
            None => None,
        };
        let created_at = normalize_required_datetime(row.created_at)?;

        let result = sqlx::query(
            r#"
            INSERT INTO waiting_on (
                id, legacy_id, project_id, description, person, last_followup, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(legacy_id) DO UPDATE SET
                project_id = excluded.project_id,
                description = excluded.description,
                person = excluded.person,
                last_followup = excluded.last_followup,
                created_at = excluded.created_at
            "#,
        )
        .bind(rust_id)
        .bind(row.id)
        .bind(project_id)
        .bind(row.description)
        .bind(optional_text(row.person))
        .bind(optional_text(row.last_followup))
        .bind(created_at)
        .execute(&mut **transaction)
        .await?;
        imported_rows += i64::try_from(result.rows_affected())
            .map_err(|error| DbError::InvalidData(error.to_string()))?;
    }

    Ok((source_rows, imported_rows, warnings))
}

fn file_sha256(path: &Path) -> Result<String, DbError> {
    let bytes = std::fs::read(path)?;
    let digest = Sha256::digest(bytes);
    Ok(format!("{digest:x}"))
}

fn unsupported_table_warnings(table_names: &[String]) -> Vec<String> {
    let supported_tables: HashSet<&'static str> = SUPPORTED_PYTHON_TABLES.iter().copied().collect();
    table_names
        .iter()
        .filter(|table| !supported_tables.contains(table.as_str()))
        .map(|table| format!("table {table} is not imported in this slice"))
        .collect()
}

fn quote_identifier(identifier: &str) -> String {
    format!("\"{}\"", identifier.replace('"', "\"\""))
}

#[derive(Debug, FromRow)]
struct LegacyProjectRow {
    id: i64,
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
struct LegacyTaskRow {
    id: i64,
    project_id: Option<i64>,
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
    owner_type: String,
    resurface_on: Option<String>,
    completed_at: Option<String>,
    created_at: String,
}

#[derive(Debug, FromRow)]
struct LegacyWaitingOnRow {
    id: i64,
    project_id: Option<i64>,
    description: String,
    person: Option<String>,
    created_at: String,
    last_followup: Option<String>,
}

#[derive(Debug, FromRow)]
struct LegacyBlockRow {
    id: i64,
    title: Option<String>,
    date: String,
    start_time: Option<String>,
    end_time: Option<String>,
    block_type: String,
    project_id: Option<i64>,
    task_id: Option<i64>,
    notes: Option<String>,
    created_at: String,
}

fn optional_text(value: Option<String>) -> Option<String> {
    value.and_then(|value| {
        let trimmed = value.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(trimmed.to_string())
        }
    })
}

fn default_text(value: String, default: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        default.to_string()
    } else {
        trimmed.to_string()
    }
}

fn normalize_required_datetime(value: String) -> Result<String, DbError> {
    normalize_datetime(&value)?.ok_or_else(|| {
        DbError::InvalidData("required datetime was empty after normalization".to_string())
    })
}

fn normalize_required_date(value: String) -> Result<String, DbError> {
    let value = value.trim();
    if value.is_empty() {
        return Err(DbError::InvalidData(
            "required date was empty after normalization".to_string(),
        ));
    }
    chrono::NaiveDate::parse_from_str(value, "%Y-%m-%d")
        .map(|date| date.to_string())
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn normalize_optional_time(value: Option<String>) -> Result<Option<String>, DbError> {
    match optional_text(value) {
        Some(value) => {
            let formats = ["%H:%M:%S%.f", "%H:%M:%S", "%H:%M"];
            for format in formats {
                if let Ok(time) = chrono::NaiveTime::parse_from_str(&value, format) {
                    return Ok(Some(time.format("%H:%M:%S").to_string()));
                }
            }
            Err(DbError::InvalidData(format!(
                "could not parse source time `{value}`"
            )))
        }
        None => Ok(None),
    }
}

fn normalize_optional_datetime(value: Option<String>) -> Result<Option<String>, DbError> {
    match optional_text(value) {
        Some(value) => normalize_datetime(&value),
        None => Ok(None),
    }
}

fn normalize_datetime(value: &str) -> Result<Option<String>, DbError> {
    let value = value.trim();
    if value.is_empty() {
        return Ok(None);
    }

    if let Ok(date_time) = DateTime::parse_from_rfc3339(value) {
        return Ok(Some(date_time.with_timezone(&Utc).to_rfc3339()));
    }

    let formats = [
        "%Y-%m-%d %H:%M:%S%.f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%.f",
        "%Y-%m-%dT%H:%M:%S",
    ];
    for format in formats {
        if let Ok(naive) = NaiveDateTime::parse_from_str(value, format) {
            let date_time = DateTime::<Utc>::from_naive_utc_and_offset(naive, Utc);
            return Ok(Some(date_time.to_rfc3339()));
        }
    }

    Err(DbError::InvalidData(format!(
        "could not parse source datetime `{value}`"
    )))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{connect, run_migrations, DbConfig};
    use sqlx::sqlite::SqliteConnectOptions;
    use std::str::FromStr;

    #[tokio::test]
    async fn import_python_sqlite_backs_up_and_imports_projects_and_tasks() {
        let source_path = temp_db_path("python-import-source");
        let backup_dir = temp_dir_path("python-import-backups");
        create_full_python_fixture(&source_path).await;
        std::fs::create_dir_all(&backup_dir).expect("create backup dir");
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect target");
        run_migrations(&pool).await.expect("migrate target");

        let report = import_python_sqlite(&pool, &source_path, &backup_dir)
            .await
            .expect("import python sqlite");

        assert_eq!(report.source_path, source_path.to_string_lossy());
        assert_eq!(report.source_sha256.len(), 64);
        assert!(std::path::Path::new(&report.backup_path).exists());
        assert_imported_table(&report.tables, "projects", 1, 1);
        assert_imported_table(&report.tables, "tasks", 2, 2);
        assert_imported_table(&report.tables, "waiting_on", 2, 2);
        assert_imported_table(&report.tables, "blocks", 2, 2);

        let project = sqlx::query_as::<_, ImportedProject>(
            "SELECT legacy_id, title, category, status, active_this_week, created_at FROM projects",
        )
        .fetch_one(&pool)
        .await
        .expect("project row");
        assert_eq!(project.legacy_id, 10);
        assert_eq!(project.title, "Legacy Project");
        assert_eq!(project.category, "personal");
        assert_eq!(project.status, "paused");
        assert_eq!(project.active_this_week, 1);
        assert_eq!(project.created_at, "2026-01-02T03:04:05+00:00");

        let tasks = sqlx::query_as::<_, ImportedTask>(
            r#"
            SELECT legacy_id, project_id, verb_noun, in_inbox, archived_from_inbox,
                   intake_intent, intake_container, when_bucket, status, owner_type, completed_at
            FROM tasks
            ORDER BY legacy_id
            "#,
        )
        .fetch_all(&pool)
        .await
        .expect("task rows");
        assert_eq!(tasks.len(), 2);
        assert_eq!(tasks[0].legacy_id, 20);
        assert!(tasks[0].project_id.is_some());
        assert_eq!(tasks[0].verb_noun, "Draft migration test");
        assert_eq!(tasks[0].in_inbox, 1);
        assert_eq!(tasks[0].archived_from_inbox, 0);
        assert_eq!(tasks[0].intake_intent, "support_project");
        assert_eq!(tasks[0].intake_container, "project");
        assert_eq!(tasks[0].when_bucket, "today");
        assert_eq!(tasks[0].status, "pending");
        assert_eq!(tasks[0].owner_type, "mine");
        assert_eq!(tasks[0].completed_at, None);
        assert_eq!(tasks[1].legacy_id, 21);
        assert_eq!(tasks[1].project_id, None);
        assert_eq!(tasks[1].status, "done");
        assert_eq!(tasks[1].owner_type, "mine");
        assert_eq!(
            tasks[1].completed_at.as_deref(),
            Some("2026-01-05T06:07:08+00:00")
        );

        let waiting = sqlx::query_as::<_, ImportedWaitingOn>(
            r#"
            SELECT legacy_id, project_id, description, person, last_followup, created_at
            FROM waiting_on
            ORDER BY legacy_id
            "#,
        )
        .fetch_all(&pool)
        .await
        .expect("waiting rows");
        assert_eq!(waiting.len(), 2);
        assert_eq!(waiting[0].legacy_id, 40);
        assert!(waiting[0].project_id.is_some());
        assert_eq!(waiting[0].description, "Waiting for review");
        assert_eq!(waiting[0].person.as_deref(), Some("Sam"));
        assert_eq!(waiting[0].last_followup.as_deref(), Some("2026-01-08"));
        assert_eq!(waiting[0].created_at, "2026-01-02T08:00:00+00:00");
        assert_eq!(waiting[1].legacy_id, 41);
        assert_eq!(waiting[1].project_id, None);

        let blocks = sqlx::query_as::<_, ImportedBlock>(
            r#"
            SELECT legacy_id, project_id, task_id, title, date, start_time, end_time,
                   block_type, notes, created_at
            FROM blocks
            ORDER BY legacy_id
            "#,
        )
        .fetch_all(&pool)
        .await
        .expect("block rows");
        assert_eq!(blocks.len(), 2);
        assert_eq!(blocks[0].legacy_id, 30);
        assert!(blocks[0].project_id.is_some());
        assert!(blocks[0].task_id.is_some());
        assert_eq!(blocks[0].title.as_deref(), Some("Legacy Focus"));
        assert_eq!(blocks[0].date, "2026-01-06");
        assert_eq!(blocks[0].start_time.as_deref(), Some("09:00:00"));
        assert_eq!(blocks[0].end_time.as_deref(), Some("09:45:00"));
        assert_eq!(blocks[0].block_type, "focus");
        assert_eq!(blocks[0].notes.as_deref(), Some("Imported"));
        assert_eq!(blocks[0].created_at, "2026-01-02T06:00:00+00:00");
        assert_eq!(blocks[1].legacy_id, 31);
        assert_eq!(blocks[1].project_id, None);
        assert_eq!(blocks[1].task_id, None);

        let _ = std::fs::remove_file(source_path);
        let _ = std::fs::remove_dir_all(backup_dir);
    }

    #[tokio::test]
    async fn import_python_sqlite_is_idempotent_by_legacy_id() {
        let source_path = temp_db_path("python-import-idempotent");
        let backup_dir = temp_dir_path("python-import-idempotent-backups");
        create_full_python_fixture(&source_path).await;
        std::fs::create_dir_all(&backup_dir).expect("create backup dir");
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect target");
        run_migrations(&pool).await.expect("migrate target");

        import_python_sqlite(&pool, &source_path, &backup_dir)
            .await
            .expect("first import");
        import_python_sqlite(&pool, &source_path, &backup_dir)
            .await
            .expect("second import");

        let project_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM projects")
            .fetch_one(&pool)
            .await
            .expect("project count");
        let task_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM tasks")
            .fetch_one(&pool)
            .await
            .expect("task count");
        let block_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM blocks")
            .fetch_one(&pool)
            .await
            .expect("block count");
        let waiting_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM waiting_on")
            .fetch_one(&pool)
            .await
            .expect("waiting count");

        assert_eq!(project_count, 1);
        assert_eq!(task_count, 2);
        assert_eq!(block_count, 2);
        assert_eq!(waiting_count, 2);

        let _ = std::fs::remove_file(source_path);
        let _ = std::fs::remove_dir_all(backup_dir);
    }

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

    fn assert_imported_table(
        tables: &[sfo_core::TableImportResult],
        name: &str,
        source_rows: i64,
        imported_rows: i64,
    ) {
        let table = tables
            .iter()
            .find(|table| table.table == name)
            .unwrap_or_else(|| panic!("missing table {name}"));

        assert_eq!(table.source_rows, source_rows);
        assert_eq!(table.imported_rows, imported_rows);
    }

    #[derive(Debug, sqlx::FromRow)]
    struct ImportedProject {
        legacy_id: i64,
        title: String,
        category: String,
        status: String,
        active_this_week: i64,
        created_at: String,
    }

    #[derive(Debug, sqlx::FromRow)]
    struct ImportedTask {
        legacy_id: i64,
        project_id: Option<String>,
        verb_noun: String,
        in_inbox: i64,
        archived_from_inbox: i64,
        intake_intent: String,
        intake_container: String,
        when_bucket: String,
        status: String,
        owner_type: String,
        completed_at: Option<String>,
    }

    #[derive(Debug, sqlx::FromRow)]
    struct ImportedWaitingOn {
        legacy_id: i64,
        project_id: Option<String>,
        description: String,
        person: Option<String>,
        last_followup: Option<String>,
        created_at: String,
    }

    #[derive(Debug, sqlx::FromRow)]
    struct ImportedBlock {
        legacy_id: i64,
        project_id: Option<String>,
        task_id: Option<String>,
        title: Option<String>,
        date: String,
        start_time: Option<String>,
        end_time: Option<String>,
        block_type: String,
        notes: Option<String>,
        created_at: String,
    }

    async fn create_full_python_fixture(path: &std::path::Path) {
        let url = format!("sqlite://{}", path.display());
        let options = SqliteConnectOptions::from_str(&url)
            .expect("sqlite options")
            .create_if_missing(true);
        let pool = sqlx::SqlitePool::connect_with(options)
            .await
            .expect("fixture connection");

        sqlx::query(
            r#"
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                color_scheme TEXT,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                size TEXT,
                time_horizon TEXT,
                start_date TEXT,
                target_date TEXT,
                level_of_success TEXT,
                why_link_text TEXT,
                drag_points_notes TEXT,
                active_this_week INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
            "#,
        )
        .execute(&pool)
        .await
        .expect("create projects");
        sqlx::query(
            r#"
            INSERT INTO projects (
                id, title, description, color_scheme, category, status, size,
                time_horizon, start_date, target_date, level_of_success, why_link_text,
                drag_points_notes, active_this_week, created_at, updated_at
            )
            VALUES (
                10, 'Legacy Project', 'Scope', NULL, 'personal', 'paused', 'moderate',
                'quarter', NULL, '2026-02-03', 'epic', 'Because it matters',
                NULL, 1, '2026-01-02 03:04:05', NULL
            )
            "#,
        )
        .execute(&pool)
        .await
        .expect("insert project");

        sqlx::query(
            r#"
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                project_id INTEGER,
                verb_noun TEXT NOT NULL,
                description TEXT,
                in_inbox INTEGER NOT NULL,
                archived_from_inbox INTEGER NOT NULL,
                intake_intent TEXT NOT NULL,
                intake_container TEXT NOT NULL,
                intake_processed_at TEXT,
                when_bucket TEXT NOT NULL,
                block_type TEXT,
                duration_minutes INTEGER,
                priority INTEGER,
                frog INTEGER NOT NULL,
                alignment TEXT,
                first_action TEXT,
                status TEXT NOT NULL,
                scheduled_for TEXT,
                owner_type TEXT NOT NULL,
                resurface_on TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL
            )
            "#,
        )
        .execute(&pool)
        .await
        .expect("create tasks");
        sqlx::query(
            r#"
            INSERT INTO tasks (
                id, project_id, verb_noun, description, in_inbox, archived_from_inbox,
                intake_intent, intake_container, intake_processed_at, when_bucket,
                block_type, duration_minutes, priority, frog, alignment, first_action,
                status, scheduled_for, owner_type, resurface_on, completed_at, created_at
            )
            VALUES
                (
                    20, 10, 'Draft migration test', 'Task scope', 1, 0,
                    'support_project', 'project', NULL, 'today',
                    'focus', 45, 1, 1, 'aligned', 'Open editor',
                    'pending', '2026-01-03', 'mine', NULL, NULL,
                    '2026-01-02 04:00:00'
                ),
                (
                    21, 999, 'Review imported data', NULL, 0, 0,
                    'unprocessed', 'unprocessed', NULL, 'later',
                    NULL, NULL, NULL, 0, NULL, NULL,
                    'done', NULL, 'mine', NULL, '2026-01-05 06:07:08',
                    '2026-01-02 05:00:00'
                )
            "#,
        )
        .execute(&pool)
        .await
        .expect("insert tasks");

        sqlx::query(
            r#"
            CREATE TABLE waiting_on (
                id INTEGER PRIMARY KEY,
                project_id INTEGER,
                description TEXT NOT NULL,
                person TEXT,
                created_at TEXT NOT NULL,
                last_followup TEXT
            )
            "#,
        )
        .execute(&pool)
        .await
        .expect("create waiting_on");
        sqlx::query(
            r#"
            INSERT INTO waiting_on (
                id, project_id, description, person, created_at, last_followup
            )
            VALUES
                (40, 10, 'Waiting for review', 'Sam', '2026-01-02 08:00:00', '2026-01-08'),
                (41, 999, 'Waiting on missing project', NULL, '2026-01-02 09:00:00', NULL)
            "#,
        )
        .execute(&pool)
        .await
        .expect("insert waiting_on");

        sqlx::query(
            r#"
            CREATE TABLE blocks (
                id INTEGER PRIMARY KEY,
                title TEXT,
                date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                block_type TEXT NOT NULL,
                project_id INTEGER,
                task_id INTEGER,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            "#,
        )
        .execute(&pool)
        .await
        .expect("create blocks");
        sqlx::query(
            r#"
            INSERT INTO blocks (
                id, title, date, start_time, end_time, block_type,
                project_id, task_id, notes, created_at
            )
            VALUES
                (
                    30, 'Legacy Focus', '2026-01-06', '09:00:00', '09:45:00',
                    'focus', 10, 20, 'Imported', '2026-01-02 06:00:00'
                ),
                (
                    31, 'Orphan Admin', '2026-01-07', NULL, NULL,
                    'admin', 999, 999, NULL, '2026-01-02 07:00:00'
                )
            "#,
        )
        .execute(&pool)
        .await
        .expect("insert blocks");

        pool.close().await;
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

    fn temp_dir_path(label: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "sfo-{label}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ))
    }
}
