use chrono::NaiveDate;
use serde::{Deserialize, Serialize};

use crate::{BlockType, Project, ProjectCategory, ProjectId, Task, TaskId, WhenBucket};

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GuidedCaptureKind {
    #[default]
    Task,
    Project,
    DecideLater,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CaptureHorizon {
    Today,
    #[default]
    Week,
    Month,
    Quarter,
    Year,
    Later,
}

impl CaptureHorizon {
    #[must_use]
    pub const fn task_when_bucket(self) -> WhenBucket {
        match self {
            Self::Today => WhenBucket::Today,
            Self::Week => WhenBucket::Week,
            Self::Month => WhenBucket::Month,
            Self::Quarter => WhenBucket::Quarter,
            Self::Year | Self::Later => WhenBucket::Later,
        }
    }

    #[must_use]
    pub const fn project_horizon(self) -> &'static str {
        match self {
            Self::Today | Self::Week => "week",
            Self::Month => "month",
            Self::Quarter => "quarter",
            Self::Year => "year",
            Self::Later => "later",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GuidedInboxIntent {
    SupportProject,
    LearnExplore,
    EnjoyRecover,
    ParkLetGo,
}

impl GuidedInboxIntent {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::SupportProject => crate::INBOX_INTENT_SUPPORT_PROJECT,
            Self::LearnExplore => crate::INBOX_INTENT_LEARN_EXPLORE,
            Self::EnjoyRecover => crate::INBOX_INTENT_ENJOY_RECOVER,
            Self::ParkLetGo => crate::INBOX_INTENT_PARK_LET_GO,
        }
    }

    #[must_use]
    pub const fn is_quick_route(self) -> bool {
        !matches!(self, Self::SupportProject)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GuidedCaptureRequest {
    pub capture_text: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub item_kind: GuidedCaptureKind,
    #[serde(default)]
    pub inbox_intent: Option<GuidedInboxIntent>,
    #[serde(default)]
    pub displacement_ack: bool,
    #[serde(default)]
    pub source_task_id: Option<TaskId>,
    #[serde(default)]
    pub category: ProjectCategory,
    #[serde(default)]
    pub project_id: Option<ProjectId>,
    #[serde(default)]
    pub horizon: CaptureHorizon,
    #[serde(default = "default_true")]
    pub include_this_week: bool,
    #[serde(default)]
    pub target_date: Option<NaiveDate>,
    #[serde(default)]
    pub verb_check_ack: bool,
    #[serde(default)]
    pub why_link_text: Option<String>,
    #[serde(default)]
    pub why_tags: Vec<String>,
    #[serde(default)]
    pub block_type: Option<BlockType>,
    #[serde(default)]
    pub duration_minutes: Option<i64>,
    #[serde(default)]
    pub frog: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GuidedCaptureResponse {
    pub message: String,
    pub task: Option<Task>,
    pub project: Option<Project>,
    pub source_task: Option<Task>,
}

fn default_true() -> bool {
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn guided_capture_request_deserializes_defaults() {
        let payload: GuidedCaptureRequest =
            serde_json::from_str(r#"{"capture_text":"Thing"}"#).expect("deserialize request");

        assert_eq!(payload.item_kind, GuidedCaptureKind::Task);
        assert_eq!(payload.horizon, CaptureHorizon::Week);
        assert!(payload.include_this_week);
    }

    #[test]
    fn capture_horizon_maps_year_to_later_for_tasks() {
        assert_eq!(CaptureHorizon::Year.task_when_bucket(), WhenBucket::Later);
        assert_eq!(CaptureHorizon::Year.project_horizon(), "year");
    }
}
