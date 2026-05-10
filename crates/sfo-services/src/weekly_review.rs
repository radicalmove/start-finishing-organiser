use chrono::{Datelike, Duration, NaiveDate};
use sfo_core::{
    ProjectCategory, Task, TaskId, TaskStatus, WeeklyFocusCount, WeeklyFocusCounts,
    WeeklyReviewSummary, WeeklyReviewTask,
};
use sfo_db::weekly_review as repo;

use crate::ServiceError;

#[derive(Clone)]
pub struct WeeklyReviewService {
    pub(crate) db: sqlx::SqlitePool,
}

impl WeeklyReviewService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn summary(
        &self,
        review_date: NaiveDate,
    ) -> Result<WeeklyReviewSummary, ServiceError> {
        let week_starts_on = week_start_monday(review_date);
        let work_count = repo::focus_count(&self.db, ProjectCategory::Work).await?;
        let personal_count = repo::focus_count(&self.db, ProjectCategory::Personal).await?;

        Ok(WeeklyReviewSummary {
            review_date,
            week_starts_on,
            focus_counts: WeeklyFocusCounts {
                work: WeeklyFocusCount {
                    category: ProjectCategory::Work,
                    current: work_count,
                    cap: ProjectCategory::Work.weekly_cap(),
                },
                personal: WeeklyFocusCount {
                    category: ProjectCategory::Personal,
                    current: personal_count,
                    cap: ProjectCategory::Personal.weekly_cap(),
                },
            },
            weekly_projects: repo::weekly_projects(&self.db).await?,
            available_projects: repo::available_projects(&self.db).await?,
            resurface_due: repo::due_resurface_tasks(&self.db, review_date)
                .await?
                .into_iter()
                .map(review_task)
                .collect(),
            completed_tasks: repo::completed_tasks_since(&self.db, week_starts_on)
                .await?
                .into_iter()
                .map(review_task)
                .collect(),
        })
    }

    pub async fn move_task_to_week(
        &self,
        id: TaskId,
    ) -> Result<WeeklyReviewTask, ServiceError> {
        let task = sfo_db::planning::get_task(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "task" })?;

        if matches!(task.status, TaskStatus::Done | TaskStatus::Archived) {
            return Err(ServiceError::Validation {
                field: "task",
                message: "done or archived tasks cannot be moved into week",
            });
        }

        let moved = repo::move_task_to_week(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "task" })?;

        Ok(review_task(moved))
    }
}

fn week_start_monday(date: NaiveDate) -> NaiveDate {
    date - Duration::days(i64::from(date.weekday().num_days_from_monday()))
}

fn review_task(task: Task) -> WeeklyReviewTask {
    WeeklyReviewTask {
        id: task.id,
        title: task.verb_noun,
        description: task.description,
        when_bucket: task.when_bucket,
        status: task.status.as_str().to_string(),
        project_id: task.project_id,
        project_title: None,
        resurface_on: task.resurface_on,
        completed_at: task.completed_at,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;
    use sfo_core::{TaskCreate, TaskStatus, WhenBucket};
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn service() -> WeeklyReviewService {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        WeeklyReviewService::new(pool)
    }

    #[tokio::test]
    async fn summary_uses_monday_week_start_and_focus_caps() {
        let service = service().await;
        let summary = service
            .summary(NaiveDate::from_ymd_opt(2026, 5, 10).unwrap())
            .await
            .expect("summary");

        assert_eq!(
            summary.week_starts_on,
            NaiveDate::from_ymd_opt(2026, 5, 4).unwrap()
        );
        assert_eq!(summary.focus_counts.work.cap, 4);
        assert_eq!(summary.focus_counts.personal.cap, 3);
    }

    #[tokio::test]
    async fn move_to_week_rejects_done_tasks() {
        let service = service().await;
        let task = sfo_db::planning::create_task(
            &service.db,
            TaskCreate {
                verb_noun: "Already complete".to_string(),
                project_id: None,
                description: None,
                in_inbox: false,
                when_bucket: WhenBucket::Month,
                block_type: None,
                duration_minutes: None,
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
                owner_type: Default::default(),
            },
        )
        .await
        .expect("task");

        let done = sfo_db::planning::update_task(
            &service.db,
            &sfo_core::Task {
                status: TaskStatus::Done,
                ..task.clone()
            },
        )
        .await
        .expect("done task");

        let error = service
            .move_task_to_week(done.id)
            .await
            .expect_err("validation error");

        assert!(format!("{error}").contains("done or archived"));
    }
}
