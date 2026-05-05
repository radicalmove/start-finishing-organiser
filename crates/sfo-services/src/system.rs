use std::path::PathBuf;

use sfo_core::{BackupManifest, ImportDryRunReport, PythonSqliteImportReport};

use crate::ServiceError;

#[derive(Clone)]
pub struct SystemService {
    db: sqlx::SqlitePool,
}

impl SystemService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn dry_run_python_sqlite_import(
        &self,
        source_path: impl Into<PathBuf>,
    ) -> Result<ImportDryRunReport, ServiceError> {
        let source_path = source_path.into();
        if source_path.as_os_str().is_empty() {
            return Err(ServiceError::Validation {
                field: "source_path",
                message: "must not be empty",
            });
        }

        sfo_db::import::dry_run_python_sqlite_import(source_path)
            .await
            .map_err(Into::into)
    }

    pub async fn import_python_sqlite(
        &self,
        source_path: impl Into<PathBuf>,
        backup_dir: Option<impl Into<PathBuf>>,
    ) -> Result<PythonSqliteImportReport, ServiceError> {
        let source_path = source_path.into();
        if source_path.as_os_str().is_empty() {
            return Err(ServiceError::Validation {
                field: "source_path",
                message: "must not be empty",
            });
        }
        let backup_dir = backup_dir
            .map(Into::into)
            .unwrap_or_else(|| PathBuf::from("backups"));
        if backup_dir.as_os_str().is_empty() {
            return Err(ServiceError::Validation {
                field: "backup_dir",
                message: "must not be empty",
            });
        }

        sfo_db::import::import_python_sqlite(&self.db, source_path, backup_dir)
            .await
            .map_err(Into::into)
    }

    pub async fn backup_manifest(&self) -> Result<BackupManifest, ServiceError> {
        sfo_db::backup::backup_manifest(&self.db)
            .await
            .map_err(Into::into)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sfo_core::{ProjectCategory, ProjectCreate};
    use sfo_db::planning::create_project;
    use sfo_db::{connect, run_migrations, DbConfig};
    use sqlx::sqlite::SqliteConnectOptions;
    use std::str::FromStr;

    async fn service() -> SystemService {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        SystemService::new(pool)
    }

    #[tokio::test]
    async fn service_delegates_import_dry_run() {
        let service = service().await;
        let path = temp_db_path("service-import");
        create_python_fixture(&path).await;

        let report = service
            .dry_run_python_sqlite_import(&path)
            .await
            .expect("dry-run report");

        assert!(report.tables.iter().any(|table| table.table == "projects"));
        assert_eq!(report.source_sha256.len(), 64);

        let _ = std::fs::remove_file(path);
    }

    #[tokio::test]
    async fn service_delegates_python_sqlite_import() {
        let service = service().await;
        let path = temp_db_path("service-import-real");
        let backup_dir = temp_dir_path("service-import-real-backups");
        create_python_fixture(&path).await;
        std::fs::create_dir_all(&backup_dir).expect("create backup dir");

        let report = service
            .import_python_sqlite(&path, Some(&backup_dir))
            .await
            .expect("import report");

        assert!(std::path::Path::new(&report.backup_path).exists());
        assert!(report
            .tables
            .iter()
            .any(|table| table.table == "projects" && table.imported_rows == 1));

        let _ = std::fs::remove_file(path);
        let _ = std::fs::remove_dir_all(backup_dir);
    }

    #[tokio::test]
    async fn service_delegates_backup_manifest() {
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

        let service = SystemService::new(pool);
        let manifest = service.backup_manifest().await.expect("manifest");

        assert_eq!(manifest.database_status, "ok");
        assert!(manifest
            .tables
            .iter()
            .any(|table| table.table == "projects" && table.rows == 1));
    }

    async fn create_python_fixture(path: &std::path::Path) {
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
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                size TEXT,
                time_horizon TEXT,
                target_date TEXT,
                level_of_success TEXT,
                why_link_text TEXT,
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
                id, title, description, category, status, size, time_horizon,
                target_date, level_of_success, why_link_text, active_this_week,
                created_at, updated_at
            )
            VALUES (
                1, 'A', NULL, 'work', 'active', NULL, NULL,
                NULL, NULL, NULL, 0, '2026-01-02 03:04:05', NULL
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
