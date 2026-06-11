use chrono::{Datelike, Duration, NaiveDate};
use sfo_core::{
    HealthCardioExercise, HealthExerciseDetails, HealthExerciseSession,
    HealthExerciseSessionCreate, HealthExerciseSessionId, HealthExerciseSessionStatus,
    HealthExerciseSessionUpdate, HealthExerciseWeek, HealthFlexibilityExercise, HealthGymExercise,
    PluginId,
};
use sfo_db::{health as repo, plugins as plugin_repo};

use crate::ServiceError;

const HEALTH_PLUGIN_ID: &str = "health";

#[derive(Clone)]
pub struct HealthService {
    db: sqlx::SqlitePool,
}

impl HealthService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn exercise_week(&self, date: NaiveDate) -> Result<HealthExerciseWeek, ServiceError> {
        self.seed_plugins().await?;
        let week_start = week_start(date)?;
        let week_end = week_end(week_start)?;
        let sessions = repo::list_week(&self.db, week_start).await?;
        Ok(HealthExerciseWeek {
            week_start,
            week_end,
            sessions,
        })
    }

    pub async fn create_exercise_session(
        &self,
        payload: HealthExerciseSessionCreate,
    ) -> Result<HealthExerciseSession, ServiceError> {
        self.ensure_health_enabled().await?;
        repo::create_session(&self.db, normalize_create(payload)?)
            .await
            .map_err(Into::into)
    }

    pub async fn get_exercise_session(
        &self,
        id: HealthExerciseSessionId,
    ) -> Result<HealthExerciseSession, ServiceError> {
        self.seed_plugins().await?;
        self.session_or_not_found(&id).await
    }

    pub async fn update_exercise_session(
        &self,
        id: HealthExerciseSessionId,
        payload: HealthExerciseSessionUpdate,
    ) -> Result<HealthExerciseSession, ServiceError> {
        self.ensure_health_enabled().await?;
        let _ = self.session_or_not_found(&id).await?;
        repo::update_session(&self.db, &id, normalize_update(payload)?)
            .await
            .map_err(Into::into)
    }

    pub async fn update_exercise_session_status(
        &self,
        id: HealthExerciseSessionId,
        status: HealthExerciseSessionStatus,
    ) -> Result<HealthExerciseSession, ServiceError> {
        self.ensure_health_enabled().await?;
        let _ = self.session_or_not_found(&id).await?;
        repo::update_session_status(&self.db, &id, status)
            .await
            .map_err(Into::into)
    }

    pub async fn delete_exercise_session(
        &self,
        id: HealthExerciseSessionId,
    ) -> Result<(), ServiceError> {
        self.ensure_health_enabled().await?;
        let _ = self.session_or_not_found(&id).await?;
        repo::delete_session(&self.db, &id)
            .await
            .map_err(Into::into)
    }

    async fn seed_plugins(&self) -> Result<(), ServiceError> {
        plugin_repo::seed_builtin_plugins(&self.db)
            .await
            .map_err(Into::into)
    }

    async fn ensure_health_enabled(&self) -> Result<(), ServiceError> {
        self.seed_plugins().await?;
        let plugin = plugin_repo::get_plugin(&self.db, &PluginId::from(HEALTH_PLUGIN_ID))
            .await?
            .ok_or(ServiceError::NotFound { entity: "plugin" })?;
        if !plugin.enabled {
            return Err(ServiceError::Validation {
                field: "plugin_id",
                message: "health plugin is disabled",
            });
        }
        Ok(())
    }

    async fn session_or_not_found(
        &self,
        id: &HealthExerciseSessionId,
    ) -> Result<HealthExerciseSession, ServiceError> {
        repo::get_session(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound {
                entity: "health exercise session",
            })
    }
}

fn normalize_create(
    mut payload: HealthExerciseSessionCreate,
) -> Result<HealthExerciseSessionCreate, ServiceError> {
    payload.title = normalize_required_text(payload.title, "title")?;
    payload.notes = normalize_optional_text(payload.notes);
    payload.target_duration_minutes =
        normalize_positive_i64(payload.target_duration_minutes, "target_duration_minutes")?;
    payload.details = normalize_details(payload.details)?;
    Ok(payload)
}

fn normalize_update(
    mut payload: HealthExerciseSessionUpdate,
) -> Result<HealthExerciseSessionUpdate, ServiceError> {
    payload.title = normalize_required_text(payload.title, "title")?;
    payload.notes = normalize_optional_text(payload.notes);
    payload.target_duration_minutes =
        normalize_positive_i64(payload.target_duration_minutes, "target_duration_minutes")?;
    payload.details = normalize_details(payload.details)?;
    Ok(payload)
}

fn normalize_details(
    mut details: HealthExerciseDetails,
) -> Result<HealthExerciseDetails, ServiceError> {
    details.gym = details
        .gym
        .into_iter()
        .map(normalize_gym_exercise)
        .collect::<Result<Vec<_>, _>>()?;
    details.cardio = details
        .cardio
        .into_iter()
        .map(normalize_cardio_exercise)
        .collect::<Result<Vec<_>, _>>()?;
    details.flexibility = details
        .flexibility
        .into_iter()
        .map(normalize_flexibility_exercise)
        .collect::<Result<Vec<_>, _>>()?;
    Ok(details)
}

fn normalize_gym_exercise(
    mut exercise: HealthGymExercise,
) -> Result<HealthGymExercise, ServiceError> {
    exercise.exercise_name = normalize_required_text(exercise.exercise_name, "exercise_name")?;
    exercise.sets = normalize_positive_i64(exercise.sets, "sets")?;
    exercise.reps = normalize_positive_i64(exercise.reps, "reps")?;
    exercise.weight = normalize_positive_f64(exercise.weight, "weight")?;
    exercise.weight_unit = normalize_optional_text(exercise.weight_unit);
    exercise.notes = normalize_optional_text(exercise.notes);
    Ok(exercise)
}

fn normalize_cardio_exercise(
    mut exercise: HealthCardioExercise,
) -> Result<HealthCardioExercise, ServiceError> {
    exercise.activity_type = normalize_required_text(exercise.activity_type, "activity_type")?;
    exercise.duration_minutes =
        normalize_positive_i64(exercise.duration_minutes, "duration_minutes")?;
    exercise.intensity = normalize_optional_text(exercise.intensity);
    exercise.notes = normalize_optional_text(exercise.notes);
    Ok(exercise)
}

fn normalize_flexibility_exercise(
    mut exercise: HealthFlexibilityExercise,
) -> Result<HealthFlexibilityExercise, ServiceError> {
    exercise.movement_name = normalize_required_text(exercise.movement_name, "movement_name")?;
    exercise.sets = normalize_positive_i64(exercise.sets, "sets")?;
    exercise.hold_seconds = normalize_positive_i64(exercise.hold_seconds, "hold_seconds")?;
    exercise.side = normalize_optional_text(exercise.side);
    exercise.notes = normalize_optional_text(exercise.notes);
    Ok(exercise)
}

fn normalize_required_text(value: String, field: &'static str) -> Result<String, ServiceError> {
    let cleaned = value.trim().to_string();
    if cleaned.is_empty() {
        return Err(ServiceError::Validation {
            field,
            message: "must not be empty",
        });
    }
    Ok(cleaned)
}

fn normalize_optional_text(value: Option<String>) -> Option<String> {
    value.and_then(|text| {
        let cleaned = text.trim().to_string();
        if cleaned.is_empty() {
            None
        } else {
            Some(cleaned)
        }
    })
}

fn normalize_positive_i64(
    value: Option<i64>,
    field: &'static str,
) -> Result<Option<i64>, ServiceError> {
    if matches!(value, Some(value) if value <= 0) {
        return Err(ServiceError::Validation {
            field,
            message: "must be greater than zero",
        });
    }
    Ok(value)
}

fn normalize_positive_f64(
    value: Option<f64>,
    field: &'static str,
) -> Result<Option<f64>, ServiceError> {
    if matches!(value, Some(value) if value <= 0.0) {
        return Err(ServiceError::Validation {
            field,
            message: "must be greater than zero",
        });
    }
    Ok(value)
}

fn week_start(date: NaiveDate) -> Result<NaiveDate, ServiceError> {
    date.checked_sub_signed(Duration::days(date.weekday().num_days_from_monday() as i64))
        .ok_or(ServiceError::Validation {
            field: "date",
            message: "week start date overflowed",
        })
}

fn week_end(week_start: NaiveDate) -> Result<NaiveDate, ServiceError> {
    week_start
        .checked_add_signed(Duration::days(6))
        .ok_or(ServiceError::Validation {
            field: "date",
            message: "week end date overflowed",
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;
    use sfo_core::{
        HealthCardioExercise, HealthExerciseDetails, HealthExerciseSessionCreate,
        HealthExerciseSessionStatus, HealthExerciseSessionType, HealthExerciseSessionUpdate,
        HealthFlexibilityExercise, HealthGymExercise, PluginId, PluginUpdate,
    };
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn services() -> (HealthService, sqlx::SqlitePool) {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        (HealthService::new(pool.clone()), pool)
    }

    async fn enable_health(pool: &sqlx::SqlitePool) {
        let plugin_service = crate::PluginService::new(pool.clone());
        plugin_service
            .seed_builtin_plugins()
            .await
            .expect("seed plugins");
        plugin_service
            .update_plugin(
                PluginId::from("health"),
                PluginUpdate {
                    enabled: Some(true),
                    ..PluginUpdate::default()
                },
            )
            .await
            .expect("enable health plugin");
    }

    #[tokio::test]
    async fn disabled_health_plugin_rejects_writes() {
        let (service, pool) = services().await;
        let existing = sfo_db::health::create_session(&pool, sample_payload())
            .await
            .expect("direct create");

        for error in [
            service
                .create_exercise_session(sample_payload())
                .await
                .expect_err("disabled create"),
            service
                .update_exercise_session(existing.id.clone(), sample_update())
                .await
                .expect_err("disabled update"),
            service
                .update_exercise_session_status(
                    existing.id.clone(),
                    HealthExerciseSessionStatus::Done,
                )
                .await
                .expect_err("disabled status"),
            service
                .delete_exercise_session(existing.id)
                .await
                .expect_err("disabled delete"),
        ] {
            assert!(matches!(
                error,
                ServiceError::Validation {
                    field: "plugin_id",
                    ..
                }
            ));
        }
    }

    #[tokio::test]
    async fn enabled_health_plugin_allows_session_lifecycle() {
        let (service, pool) = services().await;
        enable_health(&pool).await;

        let created = service
            .create_exercise_session(sample_payload())
            .await
            .expect("create");
        let updated = service
            .update_exercise_session(created.id.clone(), sample_update())
            .await
            .expect("update");
        assert_eq!(updated.title, "Zone 2 row");

        let done = service
            .update_exercise_session_status(created.id.clone(), HealthExerciseSessionStatus::Done)
            .await
            .expect("status");
        assert_eq!(done.status, HealthExerciseSessionStatus::Done);

        service
            .delete_exercise_session(created.id.clone())
            .await
            .expect("delete");
        let missing = service
            .get_exercise_session(created.id)
            .await
            .expect_err("deleted session should be missing");
        assert!(matches!(
            missing,
            ServiceError::NotFound {
                entity: "health exercise session"
            }
        ));
    }

    #[tokio::test]
    async fn exercise_week_normalizes_input_date_to_monday() {
        let (service, pool) = services().await;
        sfo_db::health::create_session(
            &pool,
            HealthExerciseSessionCreate {
                session_date: date(2026, 6, 10),
                ..sample_payload()
            },
        )
        .await
        .expect("direct create");

        let week = service
            .exercise_week(date(2026, 6, 11))
            .await
            .expect("exercise week");

        assert_eq!(week.week_start, date(2026, 6, 8));
        assert_eq!(week.week_end, date(2026, 6, 14));
        assert_eq!(week.sessions.len(), 1);
    }

    #[tokio::test]
    async fn blank_optional_text_is_normalized_to_none() {
        let (service, pool) = services().await;
        enable_health(&pool).await;
        let mut payload = sample_payload();
        payload.notes = Some("   ".to_string());
        payload.details.gym[0].weight_unit = Some("  ".to_string());
        payload.details.gym[0].notes = Some("  ".to_string());

        let session = service
            .create_exercise_session(payload)
            .await
            .expect("create session");

        assert!(session.notes.is_none());
        assert!(session.details.gym[0].weight_unit.is_none());
        assert!(session.details.gym[0].notes.is_none());
    }

    #[tokio::test]
    async fn zero_or_negative_numeric_values_are_rejected() {
        let (service, pool) = services().await;
        enable_health(&pool).await;
        let mut payload = sample_payload();
        payload.target_duration_minutes = Some(0);

        let error = service
            .create_exercise_session(payload)
            .await
            .expect_err("invalid duration");

        assert!(matches!(
            error,
            ServiceError::Validation {
                field: "target_duration_minutes",
                ..
            }
        ));

        let mut payload = sample_payload();
        payload.details.gym[0].sets = Some(-1);
        let error = service
            .create_exercise_session(payload)
            .await
            .expect_err("invalid sets");
        assert!(matches!(
            error,
            ServiceError::Validation { field: "sets", .. }
        ));
    }

    fn sample_payload() -> HealthExerciseSessionCreate {
        HealthExerciseSessionCreate {
            session_date: date(2026, 6, 8),
            session_type: HealthExerciseSessionType::Gym,
            title: "  Lower body gym  ".to_string(),
            target_duration_minutes: Some(45),
            status: HealthExerciseSessionStatus::Planned,
            notes: Some("  Keep one rep in reserve  ".to_string()),
            details: HealthExerciseDetails {
                gym: vec![HealthGymExercise {
                    id: None,
                    exercise_name: "  Back squat  ".to_string(),
                    sets: Some(3),
                    reps: Some(5),
                    weight: Some(80.0),
                    weight_unit: Some(" kg ".to_string()),
                    notes: None,
                }],
                cardio: vec![],
                flexibility: vec![],
            },
        }
    }

    fn sample_update() -> HealthExerciseSessionUpdate {
        HealthExerciseSessionUpdate {
            session_date: date(2026, 6, 10),
            session_type: HealthExerciseSessionType::Cardio,
            title: "  Zone 2 row  ".to_string(),
            target_duration_minutes: Some(20),
            status: HealthExerciseSessionStatus::Planned,
            notes: None,
            details: HealthExerciseDetails {
                gym: vec![],
                cardio: vec![HealthCardioExercise {
                    id: None,
                    activity_type: "  Indoor rowing  ".to_string(),
                    duration_minutes: Some(20),
                    intensity: Some(" Zone 2 ".to_string()),
                    notes: None,
                }],
                flexibility: vec![HealthFlexibilityExercise {
                    id: None,
                    movement_name: " Hip flexor stretch ".to_string(),
                    sets: Some(2),
                    hold_seconds: Some(45),
                    side: Some(" each ".to_string()),
                    notes: None,
                }],
            },
        }
    }

    fn date(year: i32, month: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(year, month, day).expect("date")
    }
}
