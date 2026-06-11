use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::{fmt, str::FromStr};

macro_rules! string_id_type {
    ($name:ident) => {
        #[derive(Clone, Debug, Eq, PartialEq, Hash, Serialize, Deserialize)]
        #[serde(transparent)]
        pub struct $name(String);

        impl $name {
            #[must_use]
            pub fn new(value: impl Into<String>) -> Self {
                Self(value.into())
            }

            #[must_use]
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl From<&str> for $name {
            fn from(value: &str) -> Self {
                Self(value.to_string())
            }
        }

        impl From<String> for $name {
            fn from(value: String) -> Self {
                Self(value)
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str(&self.0)
            }
        }
    };
}

macro_rules! plugin_enum {
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

        impl fmt::Display for $name {
            fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str(self.as_str())
            }
        }

        impl FromStr for $name {
            type Err = PluginEnumParseError;

            fn from_str(value: &str) -> Result<Self, Self::Err> {
                match value {
                    $($value => Ok(Self::$variant),)+
                    _ => Err(PluginEnumParseError {
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
pub struct PluginEnumParseError {
    pub enum_name: &'static str,
    pub value: String,
}

string_id_type!(PluginId);
string_id_type!(PluginCapabilityId);
string_id_type!(PluginSuggestionId);

plugin_enum!(PluginTrustLevel {
    FirstParty => "first_party",
    LocalPrivate => "local_private",
    ExternalSidecar => "external_sidecar",
});

plugin_enum!(PluginStatus {
    NotConfigured => "not_configured",
    Ready => "ready",
    Degraded => "degraded",
    Disabled => "disabled",
});

plugin_enum!(PluginCapabilityKind {
    ReadSfoContext => "read_sfo_context",
    CreateSuggestions => "create_suggestions",
    CreateTasks => "create_tasks",
    CreateWaitingItems => "create_waiting_items",
    HealthRead => "health_read",
    HealthWrite => "health_write",
    CommunicationsReadMetadata => "communications_read_metadata",
    CommunicationsReadContent => "communications_read_content",
    CommunicationsCreateDrafts => "communications_create_drafts",
    CalendarRead => "calendar_read",
    CalendarSuggestBlocks => "calendar_suggest_blocks",
});

plugin_enum!(PluginSuggestionKind {
    Task => "task",
    Waiting => "waiting",
    DraftMessage => "draft_message",
    HealthPrompt => "health_prompt",
    CalendarBlock => "calendar_block",
    Generic => "generic",
});

plugin_enum!(PluginSuggestionPriority {
    Low => "low",
    Normal => "normal",
    High => "high",
});

plugin_enum!(PluginSuggestionStatus {
    Pending => "pending",
    Approved => "approved",
    Dismissed => "dismissed",
    Superseded => "superseded",
    Failed => "failed",
});

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PluginCapability {
    pub id: PluginCapabilityId,
    pub plugin_id: PluginId,
    pub capability: PluginCapabilityKind,
    pub enabled: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PluginSummary {
    pub id: PluginId,
    pub name: String,
    pub description: Option<String>,
    pub version: String,
    pub enabled: bool,
    pub trust_level: PluginTrustLevel,
    pub status: PluginStatus,
    pub status_detail: Option<String>,
    pub capabilities: Vec<PluginCapability>,
}

pub type PluginDetail = PluginSummary;

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct PluginUpdate {
    #[serde(default)]
    pub enabled: Option<bool>,
    #[serde(default)]
    pub status: Option<PluginStatus>,
    #[serde(default)]
    pub status_detail: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PluginSuggestion {
    pub id: PluginSuggestionId,
    pub plugin_id: PluginId,
    pub kind: PluginSuggestionKind,
    pub title: String,
    pub summary: Option<String>,
    pub detail: Option<String>,
    pub payload_json: String,
    pub source_label: Option<String>,
    pub source_uri: Option<String>,
    pub confidence: Option<f64>,
    pub priority: PluginSuggestionPriority,
    pub status: PluginSuggestionStatus,
    pub created_core_kind: Option<String>,
    pub created_core_id: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub resolved_at: Option<DateTime<Utc>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PluginSuggestionCreate {
    pub plugin_id: PluginId,
    pub kind: PluginSuggestionKind,
    pub title: String,
    #[serde(default)]
    pub summary: Option<String>,
    #[serde(default)]
    pub detail: Option<String>,
    #[serde(default)]
    pub payload_json: String,
    #[serde(default)]
    pub source_label: Option<String>,
    #[serde(default)]
    pub source_uri: Option<String>,
    #[serde(default)]
    pub confidence: Option<f64>,
    #[serde(default)]
    pub priority: PluginSuggestionPriority,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct PluginSuggestionApproval {}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct PluginSuggestionDismissal {}

#[allow(clippy::derivable_impls)]
impl Default for PluginSuggestionPriority {
    fn default() -> Self {
        Self::Normal
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plugin_summary_serializes_capabilities_and_status() {
        let plugin = PluginSummary {
            id: PluginId::from("health"),
            name: "Health".to_string(),
            description: Some("Exercise and diet tracking".to_string()),
            version: "0.1.0".to_string(),
            enabled: false,
            trust_level: PluginTrustLevel::FirstParty,
            status: PluginStatus::Disabled,
            status_detail: Some("Disabled until configured".to_string()),
            capabilities: vec![PluginCapability {
                id: PluginCapabilityId::from("cap-1"),
                plugin_id: PluginId::from("health"),
                capability: PluginCapabilityKind::HealthRead,
                enabled: false,
            }],
        };

        let json = serde_json::to_value(plugin).expect("serialize plugin");
        assert_eq!(json["id"], "health");
        assert_eq!(json["trust_level"], "first_party");
        assert_eq!(json["status"], "disabled");
        assert_eq!(json["capabilities"][0]["capability"], "health_read");
    }

    #[test]
    fn plugin_suggestion_serializes_review_queue_contract() {
        let suggestion = PluginSuggestion {
            id: PluginSuggestionId::from("suggestion-1"),
            plugin_id: PluginId::from("communications"),
            kind: PluginSuggestionKind::Waiting,
            title: "Follow up with Alex".to_string(),
            summary: Some("Teams thread needs a response".to_string()),
            detail: None,
            payload_json: r#"{"description":"Follow up with Alex"}"#.to_string(),
            source_label: Some("Teams".to_string()),
            source_uri: None,
            confidence: Some(0.82),
            priority: PluginSuggestionPriority::High,
            status: PluginSuggestionStatus::Pending,
            created_core_kind: None,
            created_core_id: None,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
            resolved_at: None,
        };

        let json = serde_json::to_value(suggestion).expect("serialize suggestion");
        assert_eq!(json["kind"], "waiting");
        assert_eq!(json["priority"], "high");
        assert_eq!(json["status"], "pending");
    }
}
