use chrono::{DateTime, NaiveDate, Utc};
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

macro_rules! health_enum {
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
            type Err = HealthEnumParseError;

            fn from_str(value: &str) -> Result<Self, Self::Err> {
                match value {
                    $($value => Ok(Self::$variant),)+
                    _ => Err(HealthEnumParseError {
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
pub struct HealthEnumParseError {
    pub enum_name: &'static str,
    pub value: String,
}

string_id_type!(HealthExerciseSessionId);

health_enum!(HealthExerciseSessionType {
    Gym => "gym",
    Cardio => "cardio",
    Flexibility => "flexibility",
});

health_enum!(HealthExerciseSessionStatus {
    Planned => "planned",
    Done => "done",
    Skipped => "skipped",
});

impl Default for HealthExerciseSessionStatus {
    fn default() -> Self {
        Self::Planned
    }
}

#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct HealthExerciseDetails {
    #[serde(default)]
    pub gym: Vec<HealthGymExercise>,
    #[serde(default)]
    pub cardio: Vec<HealthCardioExercise>,
    #[serde(default)]
    pub flexibility: Vec<HealthFlexibilityExercise>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthGymExercise {
    #[serde(default)]
    pub id: Option<String>,
    pub exercise_name: String,
    #[serde(default)]
    pub sets: Option<i64>,
    #[serde(default)]
    pub reps: Option<i64>,
    #[serde(default)]
    pub weight: Option<f64>,
    #[serde(default)]
    pub weight_unit: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthCardioExercise {
    #[serde(default)]
    pub id: Option<String>,
    pub activity_type: String,
    #[serde(default)]
    pub duration_minutes: Option<i64>,
    #[serde(default)]
    pub intensity: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthFlexibilityExercise {
    #[serde(default)]
    pub id: Option<String>,
    pub movement_name: String,
    #[serde(default)]
    pub sets: Option<i64>,
    #[serde(default)]
    pub hold_seconds: Option<i64>,
    #[serde(default)]
    pub side: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthExerciseSession {
    pub id: HealthExerciseSessionId,
    pub session_date: NaiveDate,
    pub session_type: HealthExerciseSessionType,
    pub title: String,
    #[serde(default)]
    pub target_duration_minutes: Option<i64>,
    pub status: HealthExerciseSessionStatus,
    #[serde(default)]
    pub notes: Option<String>,
    #[serde(default)]
    pub details: HealthExerciseDetails,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthExerciseWeek {
    pub week_start: NaiveDate,
    pub week_end: NaiveDate,
    #[serde(default)]
    pub sessions: Vec<HealthExerciseSession>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthExerciseSessionCreate {
    pub session_date: NaiveDate,
    pub session_type: HealthExerciseSessionType,
    pub title: String,
    #[serde(default)]
    pub target_duration_minutes: Option<i64>,
    #[serde(default)]
    pub status: HealthExerciseSessionStatus,
    #[serde(default)]
    pub notes: Option<String>,
    #[serde(default)]
    pub details: HealthExerciseDetails,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthExerciseSessionUpdate {
    pub session_date: NaiveDate,
    pub session_type: HealthExerciseSessionType,
    pub title: String,
    #[serde(default)]
    pub target_duration_minutes: Option<i64>,
    #[serde(default)]
    pub status: HealthExerciseSessionStatus,
    #[serde(default)]
    pub notes: Option<String>,
    #[serde(default)]
    pub details: HealthExerciseDetails,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct HealthExerciseStatusUpdate {
    pub status: HealthExerciseSessionStatus,
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{DateTime, NaiveDate, Utc};

    #[test]
    fn health_exercise_week_serializes_sessions_and_dates() {
        let week = HealthExerciseWeek {
            week_start: NaiveDate::from_ymd_opt(2026, 6, 8).expect("week start"),
            week_end: NaiveDate::from_ymd_opt(2026, 6, 14).expect("week end"),
            sessions: vec![sample_gym_session()],
        };

        let json = serde_json::to_value(week).expect("serialize week");

        assert_eq!(json["week_start"], "2026-06-08");
        assert_eq!(json["week_end"], "2026-06-14");
        assert_eq!(json["sessions"][0]["session_type"], "gym");
        assert_eq!(json["sessions"][0]["status"], "planned");
        assert_eq!(
            json["sessions"][0]["details"]["gym"][0]["exercise_name"],
            "Back squat"
        );
    }

    #[test]
    fn health_exercise_session_serializes_typed_detail_rows() {
        let session = HealthExerciseSession {
            id: HealthExerciseSessionId::from("health-session-1"),
            session_date: NaiveDate::from_ymd_opt(2026, 6, 10).expect("date"),
            session_type: HealthExerciseSessionType::Cardio,
            title: "Zone 2 row".to_string(),
            target_duration_minutes: Some(20),
            status: HealthExerciseSessionStatus::Done,
            notes: Some("Kept it controlled".to_string()),
            details: HealthExerciseDetails {
                gym: vec![],
                cardio: vec![HealthCardioExercise {
                    id: None,
                    activity_type: "Indoor rowing".to_string(),
                    duration_minutes: Some(20),
                    intensity: Some("Zone 2".to_string()),
                    notes: None,
                }],
                flexibility: vec![],
            },
            created_at: parse_utc("2026-06-10T08:00:00Z"),
            updated_at: parse_utc("2026-06-10T08:30:00Z"),
        };

        let json = serde_json::to_value(session).expect("serialize session");

        assert_eq!(json["session_type"], "cardio");
        assert_eq!(json["status"], "done");
        assert_eq!(
            json["details"]["cardio"][0]["activity_type"],
            "Indoor rowing"
        );
        assert_eq!(json["details"]["cardio"][0]["intensity"], "Zone 2");
    }

    #[test]
    fn health_exercise_session_create_defaults_to_planned() {
        let payload: HealthExerciseSessionCreate = serde_json::from_value(serde_json::json!({
            "session_date": "2026-06-11",
            "session_type": "flexibility",
            "title": "Evening mobility",
            "details": {
                "flexibility": [
                    {
                        "movement_name": "Hip flexor stretch",
                        "sets": 2,
                        "hold_seconds": 45,
                        "side": "each"
                    }
                ]
            }
        }))
        .expect("deserialize create payload");

        assert_eq!(payload.status, HealthExerciseSessionStatus::Planned);
        assert_eq!(payload.session_type, HealthExerciseSessionType::Flexibility);
        assert_eq!(
            payload.details.flexibility[0].movement_name,
            "Hip flexor stretch"
        );
    }

    fn sample_gym_session() -> HealthExerciseSession {
        HealthExerciseSession {
            id: HealthExerciseSessionId::from("health-session-1"),
            session_date: NaiveDate::from_ymd_opt(2026, 6, 8).expect("date"),
            session_type: HealthExerciseSessionType::Gym,
            title: "Lower body gym".to_string(),
            target_duration_minutes: Some(45),
            status: HealthExerciseSessionStatus::Planned,
            notes: None,
            details: HealthExerciseDetails {
                gym: vec![HealthGymExercise {
                    id: None,
                    exercise_name: "Back squat".to_string(),
                    sets: Some(3),
                    reps: Some(5),
                    weight: Some(80.0),
                    weight_unit: Some("kg".to_string()),
                    notes: None,
                }],
                cardio: vec![],
                flexibility: vec![],
            },
            created_at: parse_utc("2026-06-08T08:00:00Z"),
            updated_at: parse_utc("2026-06-08T08:00:00Z"),
        }
    }

    fn parse_utc(value: &str) -> DateTime<Utc> {
        DateTime::parse_from_rfc3339(value)
            .expect("datetime")
            .with_timezone(&Utc)
    }
}
