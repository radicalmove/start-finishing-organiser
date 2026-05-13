use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::Task;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InboxRouteIntent {
    LearnExplore,
    EnjoyRecover,
    ParkLetGo,
}

impl InboxRouteIntent {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::LearnExplore => crate::INBOX_INTENT_LEARN_EXPLORE,
            Self::EnjoyRecover => crate::INBOX_INTENT_ENJOY_RECOVER,
            Self::ParkLetGo => crate::INBOX_INTENT_PARK_LET_GO,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct InboxRouteRequest {
    pub intent: InboxRouteIntent,
    #[serde(default)]
    pub parked_until: Option<DateTime<Utc>>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct InboxContainerCounts {
    pub unprocessed: i64,
    pub learn_explore: i64,
    pub enjoy_recover: i64,
    pub park_let_go: i64,
    pub recycle_bin: i64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct InboxContainers {
    pub counts: InboxContainerCounts,
    pub unprocessed: Vec<Task>,
    pub learning: Vec<Task>,
    pub enjoy: Vec<Task>,
    pub parked: Vec<Task>,
    pub recycle_bin: Vec<Task>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inbox_route_request_serializes_intent() {
        let request = InboxRouteRequest {
            intent: InboxRouteIntent::LearnExplore,
            parked_until: None,
        };

        let json = serde_json::to_value(&request).expect("serialize route request");

        assert_eq!(json["intent"], "learn_explore");
    }

    #[test]
    fn inbox_route_request_accepts_optional_park_until_timestamp() {
        let request: InboxRouteRequest = serde_json::from_str(
            r#"{"intent":"park_let_go","parked_until":"2026-05-14T05:30:00Z"}"#,
        )
        .expect("deserialize park until request");

        assert_eq!(request.intent, InboxRouteIntent::ParkLetGo);
        assert_eq!(
            request.parked_until.unwrap().to_rfc3339(),
            "2026-05-14T05:30:00+00:00"
        );
    }

    #[test]
    fn inbox_container_summary_serializes_counts_and_items() {
        let summary = InboxContainers {
            counts: InboxContainerCounts {
                unprocessed: 1,
                learn_explore: 2,
                enjoy_recover: 3,
                park_let_go: 4,
                recycle_bin: 5,
            },
            unprocessed: vec![],
            learning: vec![],
            enjoy: vec![],
            parked: vec![],
            recycle_bin: vec![],
        };

        let json = serde_json::to_value(&summary).expect("serialize containers");

        assert_eq!(json["counts"]["unprocessed"], 1);
        assert_eq!(json["counts"]["learn_explore"], 2);
        assert!(json["unprocessed"].as_array().unwrap().is_empty());
        assert!(json["learning"].as_array().unwrap().is_empty());
    }
}
