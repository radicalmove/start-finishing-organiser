use chrono::{DateTime, Duration, NaiveDate, Utc};
use sfo_core::{
    HealthCardioExercise, HealthExerciseDetails, HealthExerciseSession,
    HealthExerciseSessionCreate, HealthExerciseSessionId, HealthExerciseSessionStatus,
    HealthExerciseSessionUpdate, HealthFlexibilityExercise, HealthGymExercise,
};
use sqlx::{FromRow, Sqlite, Transaction};
use std::str::FromStr;

use crate::DbError;

pub async fn create_session(
    pool: &sqlx::SqlitePool,
    payload: HealthExerciseSessionCreate,
) -> Result<HealthExerciseSession, DbError> {
    let HealthExerciseSessionCreate {
        session_date,
        session_type,
        title,
        target_duration_minutes,
        status,
        notes,
        details,
    } = payload;
    let id = HealthExerciseSessionId::new(format!(
        "health-session-{}",
        Utc::now().timestamp_nanos_opt().unwrap_or_default()
    ));
    let now = now_text();
    let mut transaction = pool.begin().await?;

    sqlx::query(
        r#"
        INSERT INTO health_exercise_sessions (
          id, session_date, session_type, title, target_duration_minutes,
          status, notes, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
    .bind(id.as_str())
    .bind(format_date(session_date))
    .bind(session_type.as_str())
    .bind(title)
    .bind(target_duration_minutes)
    .bind(status.as_str())
    .bind(notes)
    .bind(&now)
    .bind(&now)
    .execute(&mut *transaction)
    .await?;

    insert_details(&mut transaction, &id, &details).await?;
    transaction.commit().await?;

    get_session(pool, &id)
        .await?
        .ok_or_else(|| DbError::InvalidData("created health session could not be loaded".into()))
}

pub async fn get_session(
    pool: &sqlx::SqlitePool,
    id: &HealthExerciseSessionId,
) -> Result<Option<HealthExerciseSession>, DbError> {
    let row = sqlx::query_as::<_, HealthExerciseSessionRow>(
        "SELECT * FROM health_exercise_sessions WHERE id = ?",
    )
    .bind(id.as_str())
    .fetch_optional(pool)
    .await?;

    match row {
        Some(row) => Ok(Some(session_from_row(pool, row).await?)),
        None => Ok(None),
    }
}

pub async fn list_week(
    pool: &sqlx::SqlitePool,
    week_start: NaiveDate,
) -> Result<Vec<HealthExerciseSession>, DbError> {
    let week_end = week_start
        .checked_add_signed(Duration::days(6))
        .ok_or_else(|| DbError::InvalidData("week end date overflowed".to_string()))?;
    let rows = sqlx::query_as::<_, HealthExerciseSessionRow>(
        r#"
        SELECT * FROM health_exercise_sessions
        WHERE session_date >= ? AND session_date <= ?
        ORDER BY session_date ASC, created_at ASC
        "#,
    )
    .bind(format_date(week_start))
    .bind(format_date(week_end))
    .fetch_all(pool)
    .await?;

    let mut sessions = Vec::with_capacity(rows.len());
    for row in rows {
        sessions.push(session_from_row(pool, row).await?);
    }
    Ok(sessions)
}

pub async fn update_session(
    pool: &sqlx::SqlitePool,
    id: &HealthExerciseSessionId,
    payload: HealthExerciseSessionUpdate,
) -> Result<HealthExerciseSession, DbError> {
    let HealthExerciseSessionUpdate {
        session_date,
        session_type,
        title,
        target_duration_minutes,
        status,
        notes,
        details,
    } = payload;
    let mut transaction = pool.begin().await?;

    sqlx::query(
        r#"
        UPDATE health_exercise_sessions
        SET session_date = ?, session_type = ?, title = ?, target_duration_minutes = ?,
            status = ?, notes = ?, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(format_date(session_date))
    .bind(session_type.as_str())
    .bind(title)
    .bind(target_duration_minutes)
    .bind(status.as_str())
    .bind(notes)
    .bind(now_text())
    .bind(id.as_str())
    .execute(&mut *transaction)
    .await?;

    replace_details(&mut transaction, id, &details).await?;
    transaction.commit().await?;

    get_session(pool, id)
        .await?
        .ok_or_else(|| DbError::InvalidData("updated health session could not be loaded".into()))
}

pub async fn update_session_status(
    pool: &sqlx::SqlitePool,
    id: &HealthExerciseSessionId,
    status: HealthExerciseSessionStatus,
) -> Result<HealthExerciseSession, DbError> {
    sqlx::query(
        r#"
        UPDATE health_exercise_sessions
        SET status = ?, updated_at = ?
        WHERE id = ?
        "#,
    )
    .bind(status.as_str())
    .bind(now_text())
    .bind(id.as_str())
    .execute(pool)
    .await?;

    get_session(pool, id).await?.ok_or_else(|| {
        DbError::InvalidData("status-updated health session could not be loaded".into())
    })
}

pub async fn delete_session(
    pool: &sqlx::SqlitePool,
    id: &HealthExerciseSessionId,
) -> Result<(), DbError> {
    sqlx::query("DELETE FROM health_exercise_sessions WHERE id = ?")
        .bind(id.as_str())
        .execute(pool)
        .await?;
    Ok(())
}

async fn session_from_row(
    pool: &sqlx::SqlitePool,
    row: HealthExerciseSessionRow,
) -> Result<HealthExerciseSession, DbError> {
    let id = HealthExerciseSessionId::from(row.id);
    let details = load_details(pool, &id).await?;
    Ok(HealthExerciseSession {
        id,
        session_date: parse_date(&row.session_date)?,
        session_type: parse_enum(&row.session_type)?,
        title: row.title,
        target_duration_minutes: row.target_duration_minutes,
        status: parse_enum(&row.status)?,
        notes: row.notes,
        details,
        created_at: parse_datetime(&row.created_at)?,
        updated_at: parse_datetime(&row.updated_at)?,
    })
}

async fn load_details(
    pool: &sqlx::SqlitePool,
    session_id: &HealthExerciseSessionId,
) -> Result<HealthExerciseDetails, DbError> {
    let gym = sqlx::query_as::<_, HealthGymExerciseRow>(
        r#"
        SELECT * FROM health_gym_exercises
        WHERE session_id = ?
        ORDER BY position ASC
        "#,
    )
    .bind(session_id.as_str())
    .fetch_all(pool)
    .await?
    .into_iter()
    .map(HealthGymExercise::from)
    .collect();
    let cardio = sqlx::query_as::<_, HealthCardioExerciseRow>(
        r#"
        SELECT * FROM health_cardio_exercises
        WHERE session_id = ?
        ORDER BY position ASC
        "#,
    )
    .bind(session_id.as_str())
    .fetch_all(pool)
    .await?
    .into_iter()
    .map(HealthCardioExercise::from)
    .collect();
    let flexibility = sqlx::query_as::<_, HealthFlexibilityExerciseRow>(
        r#"
        SELECT * FROM health_flexibility_exercises
        WHERE session_id = ?
        ORDER BY position ASC
        "#,
    )
    .bind(session_id.as_str())
    .fetch_all(pool)
    .await?
    .into_iter()
    .map(HealthFlexibilityExercise::from)
    .collect();

    Ok(HealthExerciseDetails {
        gym,
        cardio,
        flexibility,
    })
}

async fn replace_details(
    transaction: &mut Transaction<'_, Sqlite>,
    session_id: &HealthExerciseSessionId,
    details: &HealthExerciseDetails,
) -> Result<(), DbError> {
    sqlx::query("DELETE FROM health_gym_exercises WHERE session_id = ?")
        .bind(session_id.as_str())
        .execute(&mut **transaction)
        .await?;
    sqlx::query("DELETE FROM health_cardio_exercises WHERE session_id = ?")
        .bind(session_id.as_str())
        .execute(&mut **transaction)
        .await?;
    sqlx::query("DELETE FROM health_flexibility_exercises WHERE session_id = ?")
        .bind(session_id.as_str())
        .execute(&mut **transaction)
        .await?;

    insert_details(transaction, session_id, details).await
}

async fn insert_details(
    transaction: &mut Transaction<'_, Sqlite>,
    session_id: &HealthExerciseSessionId,
    details: &HealthExerciseDetails,
) -> Result<(), DbError> {
    for (position, exercise) in details.gym.iter().enumerate() {
        sqlx::query(
            r#"
            INSERT INTO health_gym_exercises (
              id, session_id, position, exercise_name, sets, reps, weight, weight_unit, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            "#,
        )
        .bind(detail_id(&exercise.id, "gym", session_id, position))
        .bind(session_id.as_str())
        .bind(position as i64)
        .bind(&exercise.exercise_name)
        .bind(exercise.sets)
        .bind(exercise.reps)
        .bind(exercise.weight)
        .bind(&exercise.weight_unit)
        .bind(&exercise.notes)
        .execute(&mut **transaction)
        .await?;
    }

    for (position, exercise) in details.cardio.iter().enumerate() {
        sqlx::query(
            r#"
            INSERT INTO health_cardio_exercises (
              id, session_id, position, activity_type, duration_minutes, intensity, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            "#,
        )
        .bind(detail_id(&exercise.id, "cardio", session_id, position))
        .bind(session_id.as_str())
        .bind(position as i64)
        .bind(&exercise.activity_type)
        .bind(exercise.duration_minutes)
        .bind(&exercise.intensity)
        .bind(&exercise.notes)
        .execute(&mut **transaction)
        .await?;
    }

    for (position, exercise) in details.flexibility.iter().enumerate() {
        sqlx::query(
            r#"
            INSERT INTO health_flexibility_exercises (
              id, session_id, position, movement_name, sets, hold_seconds, side, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            "#,
        )
        .bind(detail_id(&exercise.id, "flexibility", session_id, position))
        .bind(session_id.as_str())
        .bind(position as i64)
        .bind(&exercise.movement_name)
        .bind(exercise.sets)
        .bind(exercise.hold_seconds)
        .bind(&exercise.side)
        .bind(&exercise.notes)
        .execute(&mut **transaction)
        .await?;
    }

    Ok(())
}

#[derive(Debug, FromRow)]
struct HealthExerciseSessionRow {
    id: String,
    session_date: String,
    session_type: String,
    title: String,
    target_duration_minutes: Option<i64>,
    status: String,
    notes: Option<String>,
    created_at: String,
    updated_at: String,
}

#[derive(Debug, FromRow)]
struct HealthGymExerciseRow {
    id: String,
    exercise_name: String,
    sets: Option<i64>,
    reps: Option<i64>,
    weight: Option<f64>,
    weight_unit: Option<String>,
    notes: Option<String>,
}

impl From<HealthGymExerciseRow> for HealthGymExercise {
    fn from(row: HealthGymExerciseRow) -> Self {
        Self {
            id: Some(row.id),
            exercise_name: row.exercise_name,
            sets: row.sets,
            reps: row.reps,
            weight: row.weight,
            weight_unit: row.weight_unit,
            notes: row.notes,
        }
    }
}

#[derive(Debug, FromRow)]
struct HealthCardioExerciseRow {
    id: String,
    activity_type: String,
    duration_minutes: Option<i64>,
    intensity: Option<String>,
    notes: Option<String>,
}

impl From<HealthCardioExerciseRow> for HealthCardioExercise {
    fn from(row: HealthCardioExerciseRow) -> Self {
        Self {
            id: Some(row.id),
            activity_type: row.activity_type,
            duration_minutes: row.duration_minutes,
            intensity: row.intensity,
            notes: row.notes,
        }
    }
}

#[derive(Debug, FromRow)]
struct HealthFlexibilityExerciseRow {
    id: String,
    movement_name: String,
    sets: Option<i64>,
    hold_seconds: Option<i64>,
    side: Option<String>,
    notes: Option<String>,
}

impl From<HealthFlexibilityExerciseRow> for HealthFlexibilityExercise {
    fn from(row: HealthFlexibilityExerciseRow) -> Self {
        Self {
            id: Some(row.id),
            movement_name: row.movement_name,
            sets: row.sets,
            hold_seconds: row.hold_seconds,
            side: row.side,
            notes: row.notes,
        }
    }
}

fn detail_id(
    provided: &Option<String>,
    detail_kind: &str,
    session_id: &HealthExerciseSessionId,
    position: usize,
) -> String {
    provided
        .as_ref()
        .filter(|value| !value.trim().is_empty())
        .cloned()
        .unwrap_or_else(|| format!("{}-{detail_kind}-{}", session_id.as_str(), position + 1))
}

fn now_text() -> String {
    Utc::now().to_rfc3339()
}

fn format_date(value: NaiveDate) -> String {
    value.to_string()
}

fn parse_date(value: &str) -> Result<NaiveDate, DbError> {
    NaiveDate::parse_from_str(value, "%Y-%m-%d")
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_enum<T>(value: &str) -> Result<T, DbError>
where
    T: FromStr,
    T::Err: std::fmt::Display,
{
    value
        .parse::<T>()
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

fn parse_datetime(value: &str) -> Result<DateTime<Utc>, DbError> {
    DateTime::parse_from_rfc3339(value)
        .map(|date_time| date_time.with_timezone(&Utc))
        .map_err(|error| DbError::InvalidData(error.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{connect, run_migrations, DbConfig};
    use chrono::NaiveDate;
    use sfo_core::{
        HealthCardioExercise, HealthExerciseDetails, HealthExerciseSessionCreate,
        HealthExerciseSessionStatus, HealthExerciseSessionType, HealthExerciseSessionUpdate,
        HealthFlexibilityExercise, HealthGymExercise,
    };

    async fn migrated_pool() -> sqlx::SqlitePool {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        pool
    }

    #[tokio::test]
    async fn creates_gym_session_with_exercise_rows() {
        let pool = migrated_pool().await;

        let session = create_session(
            &pool,
            HealthExerciseSessionCreate {
                session_date: date(2026, 6, 8),
                session_type: HealthExerciseSessionType::Gym,
                title: "Lower body gym".to_string(),
                target_duration_minutes: Some(45),
                status: HealthExerciseSessionStatus::Planned,
                notes: Some("Keep one rep in reserve".to_string()),
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
            },
        )
        .await
        .expect("create session");

        assert_eq!(session.session_type, HealthExerciseSessionType::Gym);
        assert_eq!(session.details.gym.len(), 1);
        assert_eq!(session.details.gym[0].exercise_name, "Back squat");
        assert_eq!(session.details.gym[0].sets, Some(3));

        let loaded = get_session(&pool, &session.id)
            .await
            .expect("get session")
            .expect("session exists");
        assert_eq!(loaded.details.gym[0].weight, Some(80.0));
    }

    #[tokio::test]
    async fn lists_week_sessions_between_monday_and_sunday() {
        let pool = migrated_pool().await;
        create_minimal_session(&pool, date(2026, 6, 7), "Previous Sunday").await;
        let monday = create_minimal_session(&pool, date(2026, 6, 8), "Monday").await;
        let sunday = create_minimal_session(&pool, date(2026, 6, 14), "Sunday").await;
        create_minimal_session(&pool, date(2026, 6, 15), "Next Monday").await;

        let sessions = list_week(&pool, date(2026, 6, 8)).await.expect("list week");

        assert_eq!(sessions.len(), 2);
        assert_eq!(
            sessions
                .iter()
                .map(|session| session.id.clone())
                .collect::<Vec<_>>(),
            vec![monday.id, sunday.id]
        );
    }

    #[tokio::test]
    async fn updating_session_replaces_detail_rows() {
        let pool = migrated_pool().await;
        let session = create_minimal_session(&pool, date(2026, 6, 10), "Original").await;

        let updated = update_session(
            &pool,
            &session.id,
            HealthExerciseSessionUpdate {
                session_date: date(2026, 6, 11),
                session_type: HealthExerciseSessionType::Cardio,
                title: "Zone 2 row".to_string(),
                target_duration_minutes: Some(20),
                status: HealthExerciseSessionStatus::Planned,
                notes: Some("Steady pace".to_string()),
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
            },
        )
        .await
        .expect("update session");

        assert_eq!(updated.session_type, HealthExerciseSessionType::Cardio);
        assert!(updated.details.gym.is_empty());
        assert_eq!(updated.details.cardio.len(), 1);
        assert_eq!(updated.details.cardio[0].activity_type, "Indoor rowing");
    }

    #[tokio::test]
    async fn status_update_changes_status_without_replacing_session_content() {
        let pool = migrated_pool().await;
        let session = create_minimal_session(&pool, date(2026, 6, 12), "Mobility").await;
        sqlx::query("UPDATE health_exercise_sessions SET updated_at = ? WHERE id = ?")
            .bind("2026-06-01T00:00:00Z")
            .bind(session.id.as_str())
            .execute(&pool)
            .await
            .expect("set old updated timestamp");
        let before = get_session(&pool, &session.id)
            .await
            .expect("load before")
            .expect("session before");

        let updated = update_session_status(&pool, &session.id, HealthExerciseSessionStatus::Done)
            .await
            .expect("update status");

        assert_eq!(updated.status, HealthExerciseSessionStatus::Done);
        assert_eq!(updated.title, before.title);
        assert_eq!(updated.session_date, before.session_date);
        assert_eq!(updated.details, before.details);
        assert!(updated.updated_at > before.updated_at);
    }

    #[tokio::test]
    async fn deleting_session_cascades_detail_rows() {
        let pool = migrated_pool().await;
        let session = create_minimal_session(&pool, date(2026, 6, 13), "Delete me").await;

        delete_session(&pool, &session.id)
            .await
            .expect("delete session");

        assert!(get_session(&pool, &session.id)
            .await
            .expect("get deleted")
            .is_none());
        let detail_count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM health_flexibility_exercises")
                .fetch_one(&pool)
                .await
                .expect("detail count");
        assert_eq!(detail_count, 0);
    }

    async fn create_minimal_session(
        pool: &sqlx::SqlitePool,
        session_date: NaiveDate,
        title: &str,
    ) -> sfo_core::HealthExerciseSession {
        create_session(
            pool,
            HealthExerciseSessionCreate {
                session_date,
                session_type: HealthExerciseSessionType::Flexibility,
                title: title.to_string(),
                target_duration_minutes: Some(10),
                status: HealthExerciseSessionStatus::Planned,
                notes: None,
                details: HealthExerciseDetails {
                    gym: vec![],
                    cardio: vec![],
                    flexibility: vec![HealthFlexibilityExercise {
                        id: None,
                        movement_name: "Hip flexor stretch".to_string(),
                        sets: Some(2),
                        hold_seconds: Some(45),
                        side: Some("each".to_string()),
                        notes: None,
                    }],
                },
            },
        )
        .await
        .expect("create minimal session")
    }

    fn date(year: i32, month: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(year, month, day).expect("date")
    }
}
