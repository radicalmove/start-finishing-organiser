use sfo_core::{
    BlockCreate, PluginDetail, PluginId, PluginSuggestion, PluginSuggestionCreate,
    PluginSuggestionId, PluginSuggestionKind, PluginSuggestionStatus, PluginUpdate, TaskCreate,
    WaitingOnCreate,
};
use sfo_db::plugins as repo;

use crate::{PlanningService, ScheduleService, ServiceError, WaitingService};

#[derive(Clone)]
pub struct PluginService {
    db: sqlx::SqlitePool,
}

impl PluginService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn seed_builtin_plugins(&self) -> Result<(), ServiceError> {
        repo::seed_builtin_plugins(&self.db)
            .await
            .map_err(Into::into)
    }

    pub async fn list_plugins(&self) -> Result<Vec<PluginDetail>, ServiceError> {
        repo::list_plugins(&self.db).await.map_err(Into::into)
    }

    pub async fn get_plugin(&self, plugin_id: PluginId) -> Result<PluginDetail, ServiceError> {
        repo::get_plugin(&self.db, &plugin_id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "plugin" })
    }

    pub async fn update_plugin(
        &self,
        plugin_id: PluginId,
        payload: PluginUpdate,
    ) -> Result<PluginDetail, ServiceError> {
        repo::update_plugin(&self.db, &plugin_id, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn create_suggestion(
        &self,
        mut payload: PluginSuggestionCreate,
    ) -> Result<PluginSuggestion, ServiceError> {
        let plugin = self.get_plugin(payload.plugin_id.clone()).await?;
        if !plugin.enabled {
            return Err(ServiceError::Validation {
                field: "plugin_id",
                message: "plugin is disabled",
            });
        }

        payload.title = normalize_required_text(payload.title, "title")?;
        payload.summary = normalize_optional_text(payload.summary);
        payload.detail = normalize_optional_text(payload.detail);
        payload.source_label = normalize_optional_text(payload.source_label);
        payload.source_uri = normalize_optional_text(payload.source_uri);

        repo::create_suggestion(&self.db, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn list_suggestions(&self) -> Result<Vec<PluginSuggestion>, ServiceError> {
        repo::list_suggestions(&self.db, &[])
            .await
            .map_err(Into::into)
    }

    pub async fn get_suggestion(
        &self,
        suggestion_id: PluginSuggestionId,
    ) -> Result<PluginSuggestion, ServiceError> {
        repo::get_suggestion(&self.db, &suggestion_id)
            .await?
            .ok_or(ServiceError::NotFound {
                entity: "plugin suggestion",
            })
    }

    pub async fn approve_suggestion(
        &self,
        suggestion_id: PluginSuggestionId,
    ) -> Result<PluginSuggestion, ServiceError> {
        let suggestion = self.get_suggestion(suggestion_id.clone()).await?;
        if suggestion.status != PluginSuggestionStatus::Pending {
            return Err(ServiceError::Validation {
                field: "status",
                message: "suggestion is not pending",
            });
        }

        let result = match suggestion.kind {
            PluginSuggestionKind::Task => {
                let payload: TaskCreate = parse_payload(&suggestion)?;
                let task = PlanningService::new(self.db.clone())
                    .create_task(payload)
                    .await?;
                repo::mark_suggestion_approved(
                    &self.db,
                    &suggestion_id,
                    Some("task"),
                    Some(&task.id.to_string()),
                )
                .await
            }
            PluginSuggestionKind::Waiting => {
                let payload: WaitingOnCreate = parse_payload(&suggestion)?;
                let waiting = WaitingService::new(self.db.clone())
                    .create_waiting_on(payload)
                    .await?;
                repo::mark_suggestion_approved(
                    &self.db,
                    &suggestion_id,
                    Some("waiting"),
                    Some(&waiting.id.to_string()),
                )
                .await
            }
            PluginSuggestionKind::CalendarBlock => {
                let payload: BlockCreate = parse_payload(&suggestion)?;
                let block = ScheduleService::new(self.db.clone())
                    .create_block(payload)
                    .await?;
                repo::mark_suggestion_approved(
                    &self.db,
                    &suggestion_id,
                    Some("block"),
                    Some(&block.id.to_string()),
                )
                .await
            }
            PluginSuggestionKind::DraftMessage
            | PluginSuggestionKind::HealthPrompt
            | PluginSuggestionKind::Generic => {
                repo::mark_suggestion_approved(&self.db, &suggestion_id, None, None).await
            }
        };

        match result {
            Ok(suggestion) => Ok(suggestion),
            Err(error) => Err(error.into()),
        }
    }

    pub async fn dismiss_suggestion(
        &self,
        suggestion_id: PluginSuggestionId,
    ) -> Result<PluginSuggestion, ServiceError> {
        repo::mark_suggestion_dismissed(&self.db, &suggestion_id)
            .await
            .map_err(Into::into)
    }
}

fn parse_payload<T>(suggestion: &PluginSuggestion) -> Result<T, ServiceError>
where
    T: serde::de::DeserializeOwned,
{
    serde_json::from_str(&suggestion.payload_json).map_err(|_| ServiceError::Validation {
        field: "payload_json",
        message: "could not be parsed for this suggestion kind",
    })
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

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{NaiveDate, NaiveTime};
    use sfo_core::{
        BlockType, PluginId, PluginSuggestionCreate, PluginSuggestionKind,
        PluginSuggestionPriority, PluginSuggestionStatus, PluginUpdate, WhenBucket,
    };
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn services() -> (PluginService, sqlx::SqlitePool) {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        (PluginService::new(pool.clone()), pool)
    }

    fn suggestion(kind: PluginSuggestionKind, payload_json: &str) -> PluginSuggestionCreate {
        PluginSuggestionCreate {
            plugin_id: PluginId::from("health"),
            kind,
            title: "Plugin suggestion".to_string(),
            summary: None,
            detail: None,
            payload_json: payload_json.to_string(),
            source_label: Some("Health".to_string()),
            source_uri: None,
            confidence: None,
            priority: PluginSuggestionPriority::Normal,
        }
    }

    #[tokio::test]
    async fn disabled_plugin_cannot_create_suggestions() {
        let (service, _) = services().await;
        service.seed_builtin_plugins().await.expect("seed");

        let err = service
            .create_suggestion(suggestion(PluginSuggestionKind::HealthPrompt, "{}"))
            .await
            .expect_err("disabled plugin should fail");

        assert!(matches!(
            err,
            ServiceError::Validation {
                field: "plugin_id",
                ..
            }
        ));
    }

    #[tokio::test]
    async fn enabled_plugin_can_create_and_dismiss_suggestion() {
        let (service, _) = services().await;
        service.seed_builtin_plugins().await.expect("seed");
        service
            .update_plugin(
                PluginId::from("health"),
                PluginUpdate {
                    enabled: Some(true),
                    ..PluginUpdate::default()
                },
            )
            .await
            .expect("enable plugin");

        let created = service
            .create_suggestion(suggestion(PluginSuggestionKind::HealthPrompt, "{}"))
            .await
            .expect("create suggestion");
        assert_eq!(created.status, PluginSuggestionStatus::Pending);

        let dismissed = service
            .dismiss_suggestion(created.id)
            .await
            .expect("dismiss suggestion");
        assert_eq!(dismissed.status, PluginSuggestionStatus::Dismissed);
    }

    #[tokio::test]
    async fn approving_task_suggestion_creates_task() {
        let (service, pool) = services().await;
        service.seed_builtin_plugins().await.expect("seed");
        service
            .update_plugin(
                PluginId::from("health"),
                PluginUpdate {
                    enabled: Some(true),
                    ..PluginUpdate::default()
                },
            )
            .await
            .expect("enable plugin");
        let created = service
            .create_suggestion(suggestion(
                PluginSuggestionKind::Task,
                r#"{"verb_noun":"Log workout","description":"From Health","when_bucket":"today"}"#,
            ))
            .await
            .expect("create suggestion");

        let approved = service
            .approve_suggestion(created.id)
            .await
            .expect("approve task");

        assert_eq!(approved.status, PluginSuggestionStatus::Approved);
        assert_eq!(approved.created_core_kind.as_deref(), Some("task"));
        let tasks = sfo_db::planning::list_tasks(&pool, 1, 10)
            .await
            .expect("tasks");
        assert_eq!(tasks.items[0].verb_noun, "Log workout");
        assert_eq!(tasks.items[0].when_bucket, WhenBucket::Today);
    }

    #[tokio::test]
    async fn approving_waiting_suggestion_creates_waiting_item() {
        let (service, pool) = services().await;
        service.seed_builtin_plugins().await.expect("seed");
        service
            .update_plugin(
                PluginId::from("health"),
                PluginUpdate {
                    enabled: Some(true),
                    ..PluginUpdate::default()
                },
            )
            .await
            .expect("enable plugin");
        let created = service
            .create_suggestion(suggestion(
                PluginSuggestionKind::Waiting,
                r#"{"description":"Waiting for Sam","person":"Sam"}"#,
            ))
            .await
            .expect("create suggestion");

        let approved = service
            .approve_suggestion(created.id)
            .await
            .expect("approve waiting");

        assert_eq!(approved.created_core_kind.as_deref(), Some("waiting"));
        let waiting = sfo_db::waiting::list_waiting_on(&pool, 1, 10)
            .await
            .expect("waiting");
        assert_eq!(waiting.items[0].description, "Waiting for Sam");
    }

    #[tokio::test]
    async fn approving_calendar_block_suggestion_creates_block() {
        let (service, pool) = services().await;
        service.seed_builtin_plugins().await.expect("seed");
        service
            .update_plugin(
                PluginId::from("health"),
                PluginUpdate {
                    enabled: Some(true),
                    ..PluginUpdate::default()
                },
            )
            .await
            .expect("enable plugin");
        let created = service
            .create_suggestion(suggestion(
                PluginSuggestionKind::CalendarBlock,
                &format!(
                    r#"{{
                      "date":"{}",
                      "start_time":"{}",
                      "end_time":"{}",
                      "block_type":"recovery",
                      "title":"Walk"
                    }}"#,
                    NaiveDate::from_ymd_opt(2026, 6, 3).unwrap(),
                    NaiveTime::from_hms_opt(7, 0, 0).unwrap(),
                    NaiveTime::from_hms_opt(7, 30, 0).unwrap()
                ),
            ))
            .await
            .expect("create suggestion");

        let approved = service
            .approve_suggestion(created.id)
            .await
            .expect("approve block");

        assert_eq!(approved.created_core_kind.as_deref(), Some("block"));
        let blocks = sfo_db::schedule::list_blocks(&pool, 1, 10)
            .await
            .expect("blocks");
        assert_eq!(blocks.items[0].block_type, BlockType::Recovery);
    }

    #[tokio::test]
    async fn malformed_approval_payload_fails_cleanly() {
        let (service, _) = services().await;
        service.seed_builtin_plugins().await.expect("seed");
        service
            .update_plugin(
                PluginId::from("health"),
                PluginUpdate {
                    enabled: Some(true),
                    ..PluginUpdate::default()
                },
            )
            .await
            .expect("enable plugin");
        let created = service
            .create_suggestion(suggestion(PluginSuggestionKind::Task, "{not-json"))
            .await
            .expect("create malformed suggestion");

        let err = service
            .approve_suggestion(created.id)
            .await
            .expect_err("malformed payload should fail");

        assert!(matches!(
            err,
            ServiceError::Validation {
                field: "payload_json",
                ..
            }
        ));
    }
}
