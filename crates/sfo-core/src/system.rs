use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ImportDryRunRequest {
    pub source_path: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PythonSqliteImportRequest {
    pub source_path: String,
    #[serde(default)]
    pub backup_dir: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TableCount {
    pub table: String,
    pub rows: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TableImportSummary {
    pub table: String,
    pub rows: i64,
    pub supported: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ImportDryRunReport {
    pub source_path: String,
    pub source_sha256: String,
    pub tables: Vec<TableImportSummary>,
    pub warnings: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct TableImportResult {
    pub table: String,
    pub source_rows: i64,
    pub imported_rows: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PythonSqliteImportReport {
    pub source_path: String,
    pub source_sha256: String,
    pub backup_path: String,
    pub tables: Vec<TableImportResult>,
    pub warnings: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BackupManifest {
    pub generated_at: DateTime<Utc>,
    pub database_status: String,
    pub schema: String,
    pub tables: Vec<TableCount>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn import_dry_run_report_serializes_table_summaries() {
        let report = ImportDryRunReport {
            source_path: "/tmp/sfo.db".to_string(),
            source_sha256: "abc123".to_string(),
            tables: vec![TableImportSummary {
                table: "projects".to_string(),
                rows: 2,
                supported: true,
            }],
            warnings: vec!["table health_entries is not imported in this slice".to_string()],
        };

        let json = serde_json::to_value(&report).expect("serialize report");

        assert_eq!(json["source_path"], "/tmp/sfo.db");
        assert_eq!(json["tables"][0]["table"], "projects");
        assert_eq!(json["tables"][0]["rows"], 2);
        assert_eq!(json["tables"][0]["supported"], true);
    }

    #[test]
    fn python_sqlite_import_report_serializes_backup_and_results() {
        let report = PythonSqliteImportReport {
            source_path: "/tmp/source.db".to_string(),
            source_sha256: "abc123".to_string(),
            backup_path: "/tmp/backups/pre-import.db".to_string(),
            tables: vec![TableImportResult {
                table: "projects".to_string(),
                source_rows: 2,
                imported_rows: 2,
            }],
            warnings: vec![],
        };

        let json = serde_json::to_value(&report).expect("serialize report");

        assert_eq!(json["source_path"], "/tmp/source.db");
        assert_eq!(json["backup_path"], "/tmp/backups/pre-import.db");
        assert_eq!(json["tables"][0]["table"], "projects");
        assert_eq!(json["tables"][0]["source_rows"], 2);
        assert_eq!(json["tables"][0]["imported_rows"], 2);
    }

    #[test]
    fn backup_manifest_serializes_table_counts() {
        let manifest = BackupManifest {
            generated_at: DateTime::<Utc>::from_timestamp(0, 0).expect("epoch"),
            database_status: "ok".to_string(),
            schema: "sfo-rust-foundation".to_string(),
            tables: vec![TableCount {
                table: "tasks".to_string(),
                rows: 4,
            }],
        };

        let json = serde_json::to_value(&manifest).expect("serialize manifest");

        assert_eq!(json["database_status"], "ok");
        assert_eq!(json["tables"][0]["table"], "tasks");
        assert_eq!(json["tables"][0]["rows"], 4);
    }
}
