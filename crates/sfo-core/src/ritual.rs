use chrono::NaiveDate;
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RitualType {
    Morning,
    Midday,
    Evening,
}

impl RitualType {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Morning => "morning",
            Self::Midday => "midday",
            Self::Evening => "evening",
        }
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct DailyFocus {
    pub one_thing: Option<String>,
    pub frog: Option<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct DailyFocusUpdate {
    #[serde(default)]
    pub date: Option<NaiveDate>,
    #[serde(default)]
    pub one_thing: Option<String>,
    #[serde(default)]
    pub frog: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn daily_focus_update_deserializes_optional_fields() {
        let payload: DailyFocusUpdate = serde_json::from_str(
            r#"{"date":"2026-05-06","one_thing":"Ship shell","frog":"Hard call"}"#,
        )
        .expect("deserialize focus");

        assert_eq!(payload.date.unwrap().to_string(), "2026-05-06");
        assert_eq!(payload.one_thing.as_deref(), Some("Ship shell"));
        assert_eq!(payload.frog.as_deref(), Some("Hard call"));
    }
}
