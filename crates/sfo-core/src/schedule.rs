use chrono::{DateTime, NaiveDate, NaiveTime, Utc};
use serde::{Deserialize, Deserializer, Serialize};

use crate::{BlockId, BlockType, ProjectId, TaskId};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BlockCreate {
    #[serde(default)]
    pub title: Option<String>,
    pub date: NaiveDate,
    #[serde(default)]
    pub start_time: Option<NaiveTime>,
    #[serde(default)]
    pub end_time: Option<NaiveTime>,
    pub block_type: BlockType,
    #[serde(default)]
    pub project_id: Option<ProjectId>,
    #[serde(default)]
    pub task_id: Option<TaskId>,
    #[serde(default)]
    pub notes: Option<String>,
}

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct BlockUpdate {
    #[serde(default, deserialize_with = "deserialize_nullable_update")]
    pub title: Option<Option<String>>,
    #[serde(default)]
    pub date: Option<NaiveDate>,
    #[serde(default, deserialize_with = "deserialize_nullable_update")]
    pub start_time: Option<Option<NaiveTime>>,
    #[serde(default, deserialize_with = "deserialize_nullable_update")]
    pub end_time: Option<Option<NaiveTime>>,
    #[serde(default)]
    pub block_type: Option<BlockType>,
    #[serde(default, deserialize_with = "deserialize_nullable_update")]
    pub project_id: Option<Option<ProjectId>>,
    #[serde(default, deserialize_with = "deserialize_nullable_update")]
    pub task_id: Option<Option<TaskId>>,
    #[serde(default, deserialize_with = "deserialize_nullable_update")]
    pub notes: Option<Option<String>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Block {
    pub id: BlockId,
    pub title: Option<String>,
    pub date: NaiveDate,
    pub start_time: Option<NaiveTime>,
    pub end_time: Option<NaiveTime>,
    pub block_type: BlockType,
    pub project_id: Option<ProjectId>,
    pub task_id: Option<TaskId>,
    pub notes: Option<String>,
    pub created_at: DateTime<Utc>,
    pub updated_at: Option<DateTime<Utc>>,
}

fn deserialize_nullable_update<'de, D, T>(deserializer: D) -> Result<Option<Option<T>>, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer).map(Some)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn block_create_serializes_calendar_contract() {
        let payload = BlockCreate {
            title: Some("Deep work".to_string()),
            date: NaiveDate::from_ymd_opt(2026, 5, 6).expect("date"),
            start_time: Some(NaiveTime::from_hms_opt(9, 0, 0).expect("start")),
            end_time: Some(NaiveTime::from_hms_opt(10, 30, 0).expect("end")),
            block_type: BlockType::Focus,
            project_id: Some(ProjectId::new()),
            task_id: Some(TaskId::new()),
            notes: Some("No meetings".to_string()),
        };

        let json = serde_json::to_value(&payload).expect("serialize block create");

        assert_eq!(json["title"], "Deep work");
        assert_eq!(json["date"], "2026-05-06");
        assert_eq!(json["start_time"], "09:00:00");
        assert_eq!(json["end_time"], "10:30:00");
        assert_eq!(json["block_type"], "focus");
        assert!(json["project_id"].as_str().is_some());
        assert!(json["task_id"].as_str().is_some());
    }

    #[test]
    fn block_update_can_clear_optional_fields() {
        let payload = BlockUpdate {
            title: Some(None),
            project_id: Some(None),
            task_id: Some(None),
            notes: Some(None),
            ..Default::default()
        };

        let json = serde_json::to_value(&payload).expect("serialize block update");

        assert!(json["title"].is_null());
        assert!(json["project_id"].is_null());
        assert!(json["task_id"].is_null());
        assert!(json["notes"].is_null());
    }

    #[test]
    fn block_update_deserializes_explicit_null_as_clear_request() {
        let payload: BlockUpdate = serde_json::from_value(serde_json::json!({
            "title": null,
            "project_id": null,
            "notes": null
        }))
        .expect("deserialize update");

        assert_eq!(payload.title, Some(None));
        assert_eq!(payload.project_id, Some(None));
        assert_eq!(payload.notes, Some(None));
        assert_eq!(payload.task_id, None);
    }

    #[test]
    fn block_ids_round_trip_through_json() {
        let original = BlockId::new();
        let json = serde_json::to_string(&original).expect("serialize block id");
        let decoded: BlockId = serde_json::from_str(&json).expect("deserialize block id");

        assert_eq!(decoded, original);
    }
}
