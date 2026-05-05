use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct ImportDryRunRequest {
    pub source_path: String,
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
