use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};

use crate::{ProjectId, TaskId};

macro_rules! string_enum {
    ($name:ident { $($variant:ident => $value:literal),+ $(,)? }) => {
        #[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
        #[serde(rename_all = "snake_case")]
        pub enum $name {
            $($variant),+
        }

        impl $name {
            #[must_use]
            pub const fn as_str(self) -> &'static str {
                match self {
                    $(Self::$variant => $value),+
                }
            }
        }

        impl std::fmt::Display for $name {
            fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str(self.as_str())
            }
        }

        impl std::str::FromStr for $name {
            type Err = EnumParseError;

            fn from_str(value: &str) -> Result<Self, Self::Err> {
                match value {
                    $($value => Ok(Self::$variant),)+
                    _ => Err(EnumParseError {
                        enum_name: stringify!($name),
                        value: value.to_string(),
                    }),
                }
            }
        }
    };
}

#[derive(Clone, Debug, Eq, PartialEq, thiserror::Error)]
#[error("invalid {enum_name} value `{value}`")]
pub struct EnumParseError {
    pub enum_name: &'static str,
    pub value: String,
}

string_enum!(ProjectCategory {
    Work => "work",
    Personal => "personal",
});

impl ProjectCategory {
    #[must_use]
    pub const fn weekly_cap(self) -> i64 {
        match self {
            Self::Work => 4,
            Self::Personal => 3,
        }
    }
}

impl Default for ProjectCategory {
    fn default() -> Self {
        Self::Work
    }
}

string_enum!(ProjectStatus {
    Active => "active",
    Paused => "paused",
    Completed => "completed",
    Archived => "archived",
});

impl Default for ProjectStatus {
    fn default() -> Self {
        Self::Active
    }
}

string_enum!(ProjectSize {
    Light => "light",
    Moderate => "moderate",
    Heavy => "heavy",
});

string_enum!(SuccessLevel {
    Small => "small",
    Moderate => "moderate",
    Epic => "epic",
});

string_enum!(TaskStatus {
    Pending => "pending",
    InProgress => "in_progress",
    Done => "done",
    Cancelled => "cancelled",
    Archived => "archived",
});

impl Default for TaskStatus {
    fn default() -> Self {
        Self::Pending
    }
}

string_enum!(WhenBucket {
    Today => "today",
    Week => "week",
    Month => "month",
    Quarter => "quarter",
    Later => "later",
});

impl Default for WhenBucket {
    fn default() -> Self {
        Self::Later
    }
}

string_enum!(BlockType {
    Focus => "focus",
    Admin => "admin",
    Social => "social",
    Recovery => "recovery",
});

string_enum!(Alignment {
    Aligned => "aligned",
    Partial => "partial",
    Unaligned => "unaligned",
});

pub const INBOX_INTENT_UNPROCESSED: &str = "unprocessed";
pub const INBOX_INTENT_LEARN_EXPLORE: &str = "learn_explore";
pub const INBOX_INTENT_ENJOY_RECOVER: &str = "enjoy_recover";
pub const INBOX_INTENT_PARK_LET_GO: &str = "park_let_go";

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ProjectCreate {
    pub title: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub category: ProjectCategory,
    #[serde(default)]
    pub size: Option<ProjectSize>,
    #[serde(default)]
    pub time_horizon: Option<String>,
    #[serde(default)]
    pub target_date: Option<NaiveDate>,
    #[serde(default)]
    pub level_of_success: Option<SuccessLevel>,
    #[serde(default)]
    pub why_link_text: Option<String>,
    #[serde(default)]
    pub active_this_week: bool,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct ProjectUpdate {
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub status: Option<ProjectStatus>,
    #[serde(default)]
    pub category: Option<ProjectCategory>,
    #[serde(default)]
    pub size: Option<ProjectSize>,
    #[serde(default)]
    pub time_horizon: Option<String>,
    #[serde(default)]
    pub target_date: Option<NaiveDate>,
    #[serde(default)]
    pub level_of_success: Option<SuccessLevel>,
    #[serde(default)]
    pub why_link_text: Option<String>,
    #[serde(default)]
    pub active_this_week: Option<bool>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Project {
    pub id: ProjectId,
    pub title: String,
    pub description: Option<String>,
    pub category: ProjectCategory,
    pub status: ProjectStatus,
    pub size: Option<ProjectSize>,
    pub time_horizon: Option<String>,
    pub target_date: Option<NaiveDate>,
    pub level_of_success: Option<SuccessLevel>,
    pub why_link_text: Option<String>,
    pub active_this_week: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: Option<DateTime<Utc>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TaskCreate {
    pub verb_noun: String,
    #[serde(default)]
    pub project_id: Option<ProjectId>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub in_inbox: bool,
    #[serde(default)]
    pub when_bucket: WhenBucket,
    #[serde(default)]
    pub block_type: Option<BlockType>,
    #[serde(default)]
    pub duration_minutes: Option<i64>,
    #[serde(default)]
    pub priority: Option<i64>,
    #[serde(default)]
    pub frog: bool,
    #[serde(default)]
    pub alignment: Option<Alignment>,
    #[serde(default)]
    pub first_action: Option<String>,
    #[serde(default)]
    pub scheduled_for: Option<NaiveDate>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct TaskUpdate {
    #[serde(default)]
    pub verb_noun: Option<String>,
    #[serde(default)]
    pub project_id: Option<Option<ProjectId>>,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub in_inbox: Option<bool>,
    #[serde(default)]
    pub when_bucket: Option<WhenBucket>,
    #[serde(default)]
    pub block_type: Option<Option<BlockType>>,
    #[serde(default)]
    pub duration_minutes: Option<Option<i64>>,
    #[serde(default)]
    pub priority: Option<Option<i64>>,
    #[serde(default)]
    pub frog: Option<bool>,
    #[serde(default)]
    pub alignment: Option<Option<Alignment>>,
    #[serde(default)]
    pub first_action: Option<String>,
    #[serde(default)]
    pub scheduled_for: Option<Option<NaiveDate>>,
    #[serde(default)]
    pub status: Option<TaskStatus>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Task {
    pub id: TaskId,
    pub project_id: Option<ProjectId>,
    pub verb_noun: String,
    pub description: Option<String>,
    pub in_inbox: bool,
    pub archived_from_inbox: bool,
    pub intake_intent: String,
    pub intake_container: String,
    pub intake_processed_at: Option<DateTime<Utc>>,
    pub when_bucket: WhenBucket,
    pub block_type: Option<BlockType>,
    pub duration_minutes: Option<i64>,
    pub priority: Option<i64>,
    pub frog: bool,
    pub alignment: Option<Alignment>,
    pub first_action: Option<String>,
    pub status: TaskStatus,
    pub scheduled_for: Option<NaiveDate>,
    pub resurface_on: Option<NaiveDate>,
    pub completed_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: Option<DateTime<Utc>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct QuickCapture {
    pub verb_noun: String,
    #[serde(default)]
    pub description: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct Page<T> {
    pub items: Vec<T>,
    pub page: i64,
    pub page_size: i64,
    pub total: i64,
    pub total_pages: i64,
}

impl<T> Page<T> {
    #[must_use]
    pub fn new(items: Vec<T>, requested_page: i64, page_size: i64, total: i64) -> Self {
        let total_pages = if total > 0 {
            (total + page_size - 1) / page_size
        } else {
            1
        };
        let page = requested_page.clamp(1, total_pages);
        Self {
            items,
            page,
            page_size,
            total,
            total_pages,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_create_defaults_match_current_api() {
        let payload: ProjectCreate =
            serde_json::from_str(r#"{"title":"Test"}"#).expect("deserialize project");

        assert_eq!(payload.category, ProjectCategory::Work);
        assert!(!payload.active_this_week);
        assert!(payload.description.is_none());
    }

    #[test]
    fn task_create_defaults_to_later_pending_workflow() {
        let payload: TaskCreate =
            serde_json::from_str(r#"{"verb_noun":"Draft plan"}"#).expect("deserialize task");

        assert_eq!(payload.when_bucket, WhenBucket::Later);
        assert!(!payload.in_inbox);
        assert!(!payload.frog);
    }

    #[test]
    fn page_metadata_clamps_requested_page() {
        let page: Page<i32> = Page::new(vec![1, 2], 99, 2, 5);

        assert_eq!(page.page, 3);
        assert_eq!(page.total_pages, 3);
    }
}
