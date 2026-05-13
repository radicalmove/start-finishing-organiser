use chrono::Utc;
use sfo_core::{
    InboxContainers, InboxRouteIntent, InboxRouteRequest, Task, TaskId, TaskStatus, WhenBucket,
    INBOX_INTENT_ENJOY_RECOVER, INBOX_INTENT_LEARN_EXPLORE, INBOX_INTENT_PARK_LET_GO,
    INBOX_INTENT_UNPROCESSED,
};
use sfo_db::{inbox as inbox_repo, planning as planning_repo};

use crate::ServiceError;

#[derive(Clone)]
pub struct InboxService {
    db: sqlx::SqlitePool,
}

impl InboxService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn route_item(
        &self,
        id: TaskId,
        request: InboxRouteRequest,
    ) -> Result<Task, ServiceError> {
        let mut task = self.active_inbox_item_or_not_found(id).await?;
        apply_inbox_container(&mut task, request.intent, request.parked_until);
        planning_repo::update_task(&self.db, &task)
            .await
            .map_err(Into::into)
    }

    pub async fn undo_route(&self, id: TaskId) -> Result<Task, ServiceError> {
        let mut task = self.task_or_not_found(id).await?;
        if task.in_inbox {
            return Ok(task);
        }
        if !can_undo_quick_route(&task) {
            return Err(ServiceError::Validation {
                field: "task_id",
                message: "nothing to undo for this item",
            });
        }

        reset_to_unprocessed_inbox(&mut task);
        planning_repo::update_task(&self.db, &task)
            .await
            .map_err(Into::into)
    }

    pub async fn recycle_item(&self, id: TaskId) -> Result<Task, ServiceError> {
        let mut task = self.active_inbox_item_or_not_found(id).await?;
        reset_to_unprocessed_inbox(&mut task);
        task.status = TaskStatus::Archived;
        task.in_inbox = false;
        task.archived_from_inbox = true;
        task.completed_at = Some(Utc::now());
        planning_repo::update_task(&self.db, &task)
            .await
            .map_err(Into::into)
    }

    pub async fn restore_item(&self, id: TaskId) -> Result<Task, ServiceError> {
        let mut task = self.task_or_not_found(id).await?;
        if !has_restore_semantics(&task) {
            return Err(ServiceError::Validation {
                field: "task_id",
                message: "task does not have inbox restore semantics",
            });
        }

        reset_to_unprocessed_inbox(&mut task);
        planning_repo::update_task(&self.db, &task)
            .await
            .map_err(Into::into)
    }

    pub async fn containers(&self) -> Result<InboxContainers, ServiceError> {
        inbox_repo::containers(&self.db).await.map_err(Into::into)
    }

    async fn active_inbox_item_or_not_found(&self, id: TaskId) -> Result<Task, ServiceError> {
        let task = self.task_or_not_found(id).await?;
        if !task.in_inbox || !matches!(task.status, TaskStatus::Pending | TaskStatus::InProgress) {
            return Err(ServiceError::NotFound {
                entity: "inbox item",
            });
        }
        Ok(task)
    }

    async fn task_or_not_found(&self, id: TaskId) -> Result<Task, ServiceError> {
        planning_repo::get_task(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "task" })
    }
}

fn apply_inbox_container(
    task: &mut Task,
    intent: InboxRouteIntent,
    parked_until: Option<chrono::DateTime<Utc>>,
) {
    let route_intent = intent;
    let intent = route_intent.as_str().to_string();
    task.in_inbox = false;
    task.when_bucket = WhenBucket::Later;
    task.intake_intent = intent.clone();
    task.intake_container = intent;
    task.intake_processed_at = Some(Utc::now());
    task.project_id = None;
    task.block_type = None;
    task.duration_minutes = None;
    task.frog = false;
    task.alignment = None;
    task.resurface_on = None;
    task.parked_until = if matches!(route_intent, InboxRouteIntent::ParkLetGo) {
        parked_until
    } else {
        None
    };
    task.completed_at = None;
    task.status = TaskStatus::Pending;
    task.archived_from_inbox = false;
}

fn reset_to_unprocessed_inbox(task: &mut Task) {
    task.in_inbox = true;
    task.archived_from_inbox = false;
    task.when_bucket = WhenBucket::Later;
    task.status = TaskStatus::Pending;
    task.completed_at = None;
    task.parked_until = None;
    task.intake_intent = INBOX_INTENT_UNPROCESSED.to_string();
    task.intake_container = INBOX_INTENT_UNPROCESSED.to_string();
    task.intake_processed_at = None;
}

fn can_undo_quick_route(task: &Task) -> bool {
    !task.archived_from_inbox && is_quick_route_container(&task.intake_container)
}

fn has_restore_semantics(task: &Task) -> bool {
    task.archived_from_inbox || is_quick_route_container(&task.intake_container)
}

fn is_quick_route_container(container: &str) -> bool {
    matches!(
        container,
        INBOX_INTENT_LEARN_EXPLORE | INBOX_INTENT_ENJOY_RECOVER | INBOX_INTENT_PARK_LET_GO
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::PlanningService;
    use chrono::{DateTime, Utc};
    use sfo_core::{
        InboxRouteIntent, InboxRouteRequest, QuickCapture, TaskStatus, INBOX_INTENT_LEARN_EXPLORE,
        INBOX_INTENT_PARK_LET_GO,
    };
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn services() -> (PlanningService, InboxService) {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        (PlanningService::new(pool.clone()), InboxService::new(pool))
    }

    #[tokio::test]
    async fn route_to_learning_removes_item_from_inbox_and_can_undo() {
        let (planning, inbox) = services().await;
        let task = planning
            .quick_capture(QuickCapture {
                verb_noun: "Read article".to_string(),
                description: None,
            })
            .await
            .expect("quick capture");

        let routed = inbox
            .route_item(
                task.id,
                InboxRouteRequest {
                    intent: InboxRouteIntent::LearnExplore,
                    parked_until: None,
                },
            )
            .await
            .expect("route item");

        assert!(!routed.in_inbox);
        assert_eq!(routed.intake_intent, INBOX_INTENT_LEARN_EXPLORE);
        assert_eq!(routed.intake_container, INBOX_INTENT_LEARN_EXPLORE);
        assert!(routed.intake_processed_at.is_some());

        let containers = inbox.containers().await.expect("containers");
        assert_eq!(containers.counts.unprocessed, 0);
        assert_eq!(containers.counts.learn_explore, 1);
        assert_eq!(containers.learning[0].id, task.id);

        let undone = inbox.undo_route(task.id).await.expect("undo route");
        assert!(undone.in_inbox);
        assert_eq!(undone.status, TaskStatus::Pending);
        assert_eq!(undone.intake_container, sfo_core::INBOX_INTENT_UNPROCESSED);
    }

    #[tokio::test]
    async fn park_until_hides_future_items_and_returns_due_items_to_inbox() {
        let (planning, inbox) = services().await;
        let future_item = planning
            .quick_capture(QuickCapture {
                verb_noun: "Renew passport".to_string(),
                description: None,
            })
            .await
            .expect("quick capture future");
        let due_item = planning
            .quick_capture(QuickCapture {
                verb_noun: "Print calendar".to_string(),
                description: None,
            })
            .await
            .expect("quick capture due");
        let future_until = parse_utc("2099-01-01T09:00:00Z");
        let past_until = parse_utc("2026-01-01T09:00:00Z");

        let parked = inbox
            .route_item(
                future_item.id,
                InboxRouteRequest {
                    intent: InboxRouteIntent::ParkLetGo,
                    parked_until: Some(future_until),
                },
            )
            .await
            .expect("park future");
        assert!(!parked.in_inbox);
        assert_eq!(parked.intake_container, INBOX_INTENT_PARK_LET_GO);
        assert_eq!(parked.parked_until, Some(future_until));

        inbox
            .route_item(
                due_item.id,
                InboxRouteRequest {
                    intent: InboxRouteIntent::ParkLetGo,
                    parked_until: Some(past_until),
                },
            )
            .await
            .expect("park due");

        let containers = inbox.containers().await.expect("containers");

        assert_eq!(containers.counts.unprocessed, 1);
        assert_eq!(containers.counts.park_let_go, 0);
        assert_eq!(containers.unprocessed[0].id, due_item.id);
        assert!(containers.unprocessed[0].parked_until.is_none());
        assert!(containers.parked.is_empty());
    }

    #[tokio::test]
    async fn recycle_and_restore_round_trip() {
        let (planning, inbox) = services().await;
        let task = planning
            .quick_capture(QuickCapture {
                verb_noun: "Discard me".to_string(),
                description: None,
            })
            .await
            .expect("quick capture");

        let recycled = inbox.recycle_item(task.id).await.expect("recycle item");

        assert!(!recycled.in_inbox);
        assert!(recycled.archived_from_inbox);
        assert_eq!(recycled.status, TaskStatus::Archived);

        let containers = inbox.containers().await.expect("containers");
        assert_eq!(containers.counts.recycle_bin, 1);
        assert_eq!(containers.recycle_bin[0].id, task.id);

        let restored = inbox.restore_item(task.id).await.expect("restore item");
        assert!(restored.in_inbox);
        assert!(!restored.archived_from_inbox);
        assert_eq!(restored.status, TaskStatus::Pending);
    }

    fn parse_utc(value: &str) -> DateTime<Utc> {
        DateTime::parse_from_rfc3339(value)
            .expect("datetime")
            .with_timezone(&Utc)
    }
}
