use sfo_core::{Block, BlockCreate, BlockId, BlockUpdate, Page};
use sfo_db::schedule as repo;

use crate::ServiceError;

#[derive(Clone)]
pub struct ScheduleService {
    db: sqlx::SqlitePool,
}

impl ScheduleService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn create_block(&self, mut payload: BlockCreate) -> Result<Block, ServiceError> {
        payload.title = normalize_optional_text(payload.title);
        payload.notes = normalize_optional_text(payload.notes);
        validate_time_order(payload.start_time, payload.end_time)?;
        repo::create_block(&self.db, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn list_blocks(
        &self,
        page: i64,
        page_size: i64,
    ) -> Result<Page<Block>, ServiceError> {
        repo::list_blocks(&self.db, page, page_size)
            .await
            .map_err(Into::into)
    }

    pub async fn update_block(
        &self,
        id: BlockId,
        mut payload: BlockUpdate,
    ) -> Result<Block, ServiceError> {
        if let Some(title) = payload.title {
            payload.title = Some(normalize_optional_text(title));
        }
        if let Some(notes) = payload.notes {
            payload.notes = Some(normalize_optional_text(notes));
        }
        validate_time_order_for_update(payload.start_time, payload.end_time)?;
        repo::update_block(&self.db, id, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn delete_block(&self, id: BlockId) -> Result<(), ServiceError> {
        if repo::delete_block(&self.db, id).await? {
            Ok(())
        } else {
            Err(ServiceError::NotFound { entity: "block" })
        }
    }
}

fn normalize_optional_text(value: Option<String>) -> Option<String> {
    value.and_then(|text| {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(trimmed.to_string())
        }
    })
}

fn validate_time_order(
    start_time: Option<chrono::NaiveTime>,
    end_time: Option<chrono::NaiveTime>,
) -> Result<(), ServiceError> {
    if let (Some(start_time), Some(end_time)) = (start_time, end_time) {
        if end_time <= start_time {
            return Err(ServiceError::Validation {
                field: "end_time",
                message: "must be after start_time",
            });
        }
    }
    Ok(())
}

fn validate_time_order_for_update(
    start_time: Option<Option<chrono::NaiveTime>>,
    end_time: Option<Option<chrono::NaiveTime>>,
) -> Result<(), ServiceError> {
    match (start_time, end_time) {
        (Some(start_time), Some(end_time)) => validate_time_order(start_time, end_time),
        _ => Ok(()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::PlanningService;
    use chrono::{NaiveDate, NaiveTime};
    use sfo_core::{
        BlockCreate, BlockType, ProjectCategory, ProjectCreate, TaskCreate, WhenBucket,
    };
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn services() -> (PlanningService, ScheduleService) {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        (
            PlanningService::new(pool.clone()),
            ScheduleService::new(pool),
        )
    }

    #[tokio::test]
    async fn service_creates_and_deletes_task_blocks() {
        let (planning, schedule) = services().await;
        let project = planning
            .create_project(ProjectCreate {
                title: "Project".to_string(),
                description: None,
                category: ProjectCategory::Work,
                size: None,
                time_horizon: None,
                target_date: None,
                level_of_success: None,
                why_link_text: None,
                active_this_week: false,
            })
            .await
            .expect("project");
        let task = planning
            .create_task(TaskCreate {
                verb_noun: "Schedule task".to_string(),
                project_id: Some(project.id),
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Today,
                block_type: Some(BlockType::Focus),
                duration_minutes: Some(45),
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            })
            .await
            .expect("task");
        let block_date = NaiveDate::from_ymd_opt(2026, 5, 6).expect("date");

        let block = schedule
            .create_block(BlockCreate {
                title: Some("Focus".to_string()),
                date: block_date,
                start_time: Some(NaiveTime::from_hms_opt(9, 0, 0).expect("start")),
                end_time: Some(NaiveTime::from_hms_opt(9, 45, 0).expect("end")),
                block_type: BlockType::Focus,
                project_id: Some(project.id),
                task_id: Some(task.id),
                notes: None,
            })
            .await
            .expect("block");

        assert_eq!(block.project_id, Some(project.id));
        assert_eq!(block.task_id, Some(task.id));

        let scheduled = planning.get_task(task.id).await.expect("task");
        assert_eq!(scheduled.scheduled_for, Some(block_date));

        schedule.delete_block(block.id).await.expect("delete");

        let unscheduled = planning.get_task(task.id).await.expect("task");
        assert_eq!(unscheduled.scheduled_for, None);
    }
}
