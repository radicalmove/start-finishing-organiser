use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};

use crate::{ProjectId, WaitingId};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WaitingOnCreate {
    pub description: String,
    #[serde(default)]
    pub person: Option<String>,
    #[serde(default)]
    pub project_id: Option<ProjectId>,
    #[serde(default)]
    pub last_followup: Option<NaiveDate>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct WaitingOnUpdate {
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default, deserialize_with = "deserialize_present_option")]
    pub person: Option<Option<String>>,
    #[serde(default, deserialize_with = "deserialize_present_option")]
    pub project_id: Option<Option<ProjectId>>,
    #[serde(default, deserialize_with = "deserialize_present_option")]
    pub last_followup: Option<Option<NaiveDate>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WaitingOn {
    pub id: WaitingId,
    pub project_id: Option<ProjectId>,
    pub description: String,
    pub person: Option<String>,
    pub last_followup: Option<NaiveDate>,
    pub created_at: DateTime<Utc>,
    pub updated_at: Option<DateTime<Utc>>,
}

fn deserialize_present_option<'de, D, T>(deserializer: D) -> Result<Option<Option<T>>, D::Error>
where
    D: serde::Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer).map(Some)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn waiting_on_update_can_clear_followup() {
        let payload: WaitingOnUpdate =
            serde_json::from_str(r#"{"last_followup":null}"#).expect("deserialize update");

        assert_eq!(payload.last_followup, Some(None));
    }
}
