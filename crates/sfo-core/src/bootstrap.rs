use chrono::{NaiveDate, NaiveTime};
use serde::{Deserialize, Serialize};

use crate::{Block, Project, TableCount, Task};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BootstrapSummary {
    pub today: NaiveDate,
    pub current_time: Option<NaiveTime>,
    pub weekly_projects: Vec<Project>,
    pub inbox: BootstrapInboxSummary,
    pub today_tasks: Vec<Task>,
    pub today_blocks: Vec<Block>,
    pub current_block: Option<Block>,
    pub next_block: Option<Block>,
    pub daily_focus: BootstrapDailyFocus,
    pub rituals: BootstrapRitualSummary,
    pub waiting: BootstrapWaitingSummary,
    pub system: BootstrapSystemSummary,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct BootstrapInboxSummary {
    pub unprocessed: i64,
    pub learn_explore: i64,
    pub enjoy_recover: i64,
    pub park_let_go: i64,
    pub recycle_bin: i64,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct BootstrapDailyFocus {
    pub one_thing: Option<String>,
    pub frog: Option<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct BootstrapRitualSummary {
    pub morning: bool,
    pub midday: bool,
    pub evening: bool,
    pub next_key: Option<String>,
    pub next_label: Option<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct BootstrapWaitingSummary {
    pub total: i64,
    pub due: i64,
    pub overdue: i64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct BootstrapSystemSummary {
    pub database_status: String,
    pub schema: String,
    pub backup_tables: Vec<TableCount>,
    pub import_supported_tables: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bootstrap_inbox_summary_serializes_counts() {
        let summary = BootstrapInboxSummary {
            unprocessed: 3,
            learn_explore: 2,
            enjoy_recover: 1,
            park_let_go: 4,
            recycle_bin: 5,
        };

        let json = serde_json::to_value(&summary).expect("serialize inbox summary");

        assert_eq!(json["unprocessed"], 3);
        assert_eq!(json["learn_explore"], 2);
        assert_eq!(json["enjoy_recover"], 1);
        assert_eq!(json["park_let_go"], 4);
        assert_eq!(json["recycle_bin"], 5);
    }

    #[test]
    fn bootstrap_system_summary_serializes_import_and_backup_state() {
        let summary = BootstrapSystemSummary {
            database_status: "ok".to_string(),
            schema: "sfo-rust-foundation".to_string(),
            backup_tables: vec![TableCount {
                table: "blocks".to_string(),
                rows: 2,
            }],
            import_supported_tables: vec!["projects".to_string(), "tasks".to_string()],
        };

        let json = serde_json::to_value(&summary).expect("serialize system summary");

        assert_eq!(json["database_status"], "ok");
        assert_eq!(json["backup_tables"][0]["table"], "blocks");
        assert_eq!(json["import_supported_tables"][0], "projects");
    }

    #[test]
    fn bootstrap_daily_context_serializes_focus_rituals_and_waiting() {
        let focus = BootstrapDailyFocus {
            one_thing: Some("Ship shell".to_string()),
            frog: Some("Hard call".to_string()),
        };
        let rituals = BootstrapRitualSummary {
            morning: true,
            midday: false,
            evening: false,
            next_key: Some("midday".to_string()),
            next_label: Some("Midday reset".to_string()),
        };
        let waiting = BootstrapWaitingSummary {
            total: 2,
            due: 1,
            overdue: 0,
        };

        let json = serde_json::json!({
            "daily_focus": focus,
            "rituals": rituals,
            "waiting": waiting
        });

        assert_eq!(json["daily_focus"]["one_thing"], "Ship shell");
        assert_eq!(json["rituals"]["next_key"], "midday");
        assert_eq!(json["waiting"]["due"], 1);
    }
}
