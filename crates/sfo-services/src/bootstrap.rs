use chrono::{NaiveDate, NaiveTime};
use sfo_core::{Block, BootstrapSummary, BootstrapSystemSummary};

use crate::ServiceError;

#[derive(Clone)]
pub struct BootstrapService {
    db: sqlx::SqlitePool,
}

impl BootstrapService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn summary(
        &self,
        today: NaiveDate,
        current_time: Option<NaiveTime>,
    ) -> Result<BootstrapSummary, ServiceError> {
        let weekly_projects = sfo_db::bootstrap::active_weekly_projects(&self.db).await?;
        let inbox = sfo_db::bootstrap::inbox_summary(&self.db).await?;
        let today_tasks = sfo_db::bootstrap::today_tasks(&self.db, today).await?;
        let today_blocks = sfo_db::bootstrap::today_blocks(&self.db, today).await?;
        let current_block = current_time.and_then(|time| current_block(&today_blocks, time));
        let next_block = current_time.and_then(|time| next_block(&today_blocks, time));
        let backup = sfo_db::backup::backup_manifest(&self.db).await?;
        let system = BootstrapSystemSummary {
            database_status: backup.database_status,
            schema: backup.schema,
            backup_tables: backup.tables,
            import_supported_tables: sfo_db::import::SUPPORTED_PYTHON_TABLES
                .iter()
                .map(|table| (*table).to_string())
                .collect(),
        };

        Ok(BootstrapSummary {
            today,
            current_time,
            weekly_projects,
            inbox,
            today_tasks,
            today_blocks,
            current_block,
            next_block,
            system,
        })
    }
}

fn current_block(blocks: &[Block], time: NaiveTime) -> Option<Block> {
    blocks
        .iter()
        .find(|block| match (block.start_time, block.end_time) {
            (Some(start), Some(end)) => start <= time && time <= end,
            _ => false,
        })
        .cloned()
}

fn next_block(blocks: &[Block], time: NaiveTime) -> Option<Block> {
    blocks
        .iter()
        .filter(|block| block.start_time.is_some_and(|start| start > time))
        .min_by_key(|block| block.start_time)
        .cloned()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{PlanningService, ScheduleService};
    use chrono::{NaiveDate, NaiveTime};
    use sfo_core::{
        BlockCreate, BlockType, ProjectCategory, ProjectCreate, QuickCapture, TaskCreate,
        WhenBucket,
    };
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn services() -> (PlanningService, ScheduleService, BootstrapService) {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        (
            PlanningService::new(pool.clone()),
            ScheduleService::new(pool.clone()),
            BootstrapService::new(pool),
        )
    }

    #[tokio::test]
    async fn summary_returns_current_and_next_blocks_for_today() {
        let (planning, schedule, bootstrap) = services().await;
        let today = NaiveDate::from_ymd_opt(2026, 5, 6).expect("today");
        let project = planning
            .create_project(ProjectCreate {
                title: "Weekly".to_string(),
                description: None,
                category: ProjectCategory::Work,
                size: None,
                time_horizon: None,
                target_date: None,
                level_of_success: None,
                why_link_text: None,
                active_this_week: true,
            })
            .await
            .expect("project");
        planning
            .create_task(TaskCreate {
                verb_noun: "Today task".to_string(),
                project_id: Some(project.id),
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Today,
                block_type: Some(BlockType::Focus),
                duration_minutes: Some(30),
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
            })
            .await
            .expect("task");
        planning
            .quick_capture(QuickCapture {
                verb_noun: "Inbox".to_string(),
                description: None,
            })
            .await
            .expect("inbox");
        schedule
            .create_block(BlockCreate {
                title: Some("Current".to_string()),
                date: today,
                start_time: Some(NaiveTime::from_hms_opt(9, 0, 0).expect("start")),
                end_time: Some(NaiveTime::from_hms_opt(10, 0, 0).expect("end")),
                block_type: BlockType::Focus,
                project_id: Some(project.id),
                task_id: None,
                notes: None,
            })
            .await
            .expect("current block");
        schedule
            .create_block(BlockCreate {
                title: Some("Next".to_string()),
                date: today,
                start_time: Some(NaiveTime::from_hms_opt(11, 0, 0).expect("start")),
                end_time: Some(NaiveTime::from_hms_opt(12, 0, 0).expect("end")),
                block_type: BlockType::Admin,
                project_id: None,
                task_id: None,
                notes: None,
            })
            .await
            .expect("next block");

        let summary = bootstrap
            .summary(
                today,
                Some(NaiveTime::from_hms_opt(9, 30, 0).expect("time")),
            )
            .await
            .expect("summary");

        assert_eq!(summary.weekly_projects.len(), 1);
        assert_eq!(summary.inbox.unprocessed, 1);
        assert_eq!(summary.today_tasks.len(), 1);
        assert_eq!(summary.today_blocks.len(), 2);
        assert_eq!(
            summary.current_block.and_then(|block| block.title),
            Some("Current".to_string())
        );
        assert_eq!(
            summary.next_block.and_then(|block| block.title),
            Some("Next".to_string())
        );
        assert!(summary
            .system
            .import_supported_tables
            .iter()
            .any(|table| table == "blocks"));
    }
}
