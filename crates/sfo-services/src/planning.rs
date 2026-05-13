use chrono::Utc;
use sfo_core::{
    Page, Project, ProjectCard, ProjectCardUpdate, ProjectCategory, ProjectChunkCreate,
    ProjectCreate, ProjectId, ProjectUpdate, QuickCapture, SuccessPackUpdate, Task, TaskCreate,
    TaskId, TaskStatus, TaskUpdate, WhenBucket, INBOX_INTENT_UNPROCESSED,
};
use sfo_db::planning as repo;

use crate::ServiceError;

#[derive(Clone)]
pub struct PlanningService {
    db: sqlx::SqlitePool,
}

impl PlanningService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn create_project(
        &self,
        mut payload: ProjectCreate,
    ) -> Result<Project, ServiceError> {
        payload.title = normalize_title(payload.title, "title")?;
        payload.description = normalize_optional_text(payload.description);
        payload.time_horizon = normalize_optional_text(payload.time_horizon);
        payload.why_link_text = normalize_optional_text(payload.why_link_text);
        payload.drag_points_notes = normalize_optional_text(payload.drag_points_notes);
        payload.gates_notes = normalize_optional_text(payload.gates_notes);
        payload.budget_notes = normalize_optional_text(payload.budget_notes);
        ensure_weekly_cap(&self.db, payload.category, payload.active_this_week).await?;
        repo::create_project(&self.db, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn list_projects(
        &self,
        page: i64,
        page_size: i64,
    ) -> Result<Page<Project>, ServiceError> {
        repo::list_projects(&self.db, page, page_size)
            .await
            .map_err(Into::into)
    }

    pub async fn update_project(
        &self,
        id: ProjectId,
        payload: ProjectUpdate,
    ) -> Result<Project, ServiceError> {
        let mut project = self.project_or_not_found(id).await?;
        let target_category = payload.category.unwrap_or(project.category);
        let target_active = payload.active_this_week.unwrap_or(project.active_this_week);
        let needs_new_active_slot =
            target_active && !(project.active_this_week && project.category == target_category);

        ensure_weekly_cap(&self.db, target_category, needs_new_active_slot).await?;

        if let Some(title) = payload.title {
            project.title = normalize_title(title, "title")?;
        }
        if let Some(description) = payload.description {
            project.description = normalize_optional_text(Some(description));
        }
        if let Some(status) = payload.status {
            project.status = status;
        }
        project.category = target_category;
        if let Some(size) = payload.size {
            project.size = Some(size);
        }
        if let Some(time_horizon) = payload.time_horizon {
            project.time_horizon = normalize_optional_text(Some(time_horizon));
        }
        if let Some(start_date) = payload.start_date {
            project.start_date = Some(start_date);
        }
        if let Some(target_date) = payload.target_date {
            project.target_date = Some(target_date);
        }
        if let Some(level_of_success) = payload.level_of_success {
            project.level_of_success = Some(level_of_success);
        }
        if let Some(why_link_text) = payload.why_link_text {
            project.why_link_text = normalize_optional_text(Some(why_link_text));
        }
        if let Some(drag_points_notes) = payload.drag_points_notes {
            project.drag_points_notes = normalize_optional_text(Some(drag_points_notes));
        }
        if let Some(gates_notes) = payload.gates_notes {
            project.gates_notes = normalize_optional_text(Some(gates_notes));
        }
        if let Some(budget_notes) = payload.budget_notes {
            project.budget_notes = normalize_optional_text(Some(budget_notes));
        }
        if let Some(active_this_week) = payload.active_this_week {
            project.active_this_week = active_this_week;
        }

        repo::update_project(&self.db, &project)
            .await
            .map_err(Into::into)
    }

    pub async fn delete_project(&self, id: ProjectId) -> Result<(), ServiceError> {
        if repo::delete_project(&self.db, id).await? {
            Ok(())
        } else {
            Err(ServiceError::NotFound { entity: "project" })
        }
    }

    pub async fn get_project_card(&self, id: ProjectId) -> Result<ProjectCard, ServiceError> {
        repo::get_project_card(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "project" })
    }

    pub async fn save_project_card(
        &self,
        id: ProjectId,
        payload: ProjectCardUpdate,
    ) -> Result<ProjectCard, ServiceError> {
        let mut project = self.project_or_not_found(id).await?;
        let title = normalize_title(payload.title, "title")?;
        if !project_title_looks_action(&title) && !payload.verb_check_ack {
            return Err(ServiceError::Validation {
                field: "title",
                message: "project title should start with an action verb",
            });
        }
        let target_date = payload.target_date.ok_or(ServiceError::Validation {
            field: "target_date",
            message: "Set a target date for this project. No date = no finish.",
        })?;

        let needs_new_active_slot = payload.active_this_week
            && !(project.active_this_week && project.category == payload.category);
        ensure_weekly_cap(&self.db, payload.category, needs_new_active_slot).await?;

        project.title = title;
        project.description = normalize_optional_text(payload.description);
        project.status = payload.status;
        project.category = payload.category;
        project.size = payload.size;
        project.time_horizon = normalize_optional_text(payload.time_horizon);
        project.start_date = payload.start_date;
        project.target_date = Some(target_date);
        project.level_of_success = payload.level_of_success;
        project.why_link_text = normalize_optional_text(payload.why_link_text);
        project.drag_points_notes = normalize_optional_text(payload.drag_points_notes);
        project.gates_notes = normalize_optional_text(payload.gates_notes);
        project.budget_notes = normalize_optional_text(payload.budget_notes);
        project.active_this_week = payload.active_this_week;

        repo::update_project(&self.db, &project).await?;
        if let Some(success_pack) = payload.success_pack {
            repo::upsert_success_pack(&self.db, id, normalize_success_pack(success_pack)).await?;
        }

        self.get_project_card(id).await
    }

    pub async fn create_project_chunk(
        &self,
        project_id: ProjectId,
        mut payload: ProjectChunkCreate,
    ) -> Result<Task, ServiceError> {
        let _ = self.project_or_not_found(project_id).await?;
        payload.verb_noun = normalize_title(payload.verb_noun, "verb_noun")?;
        payload.description = normalize_optional_text(payload.description);
        payload.duration_minutes = payload.duration_minutes.filter(|value| *value > 0);
        repo::create_project_chunk(&self.db, project_id, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn create_task(&self, mut payload: TaskCreate) -> Result<Task, ServiceError> {
        payload.verb_noun = normalize_title(payload.verb_noun, "verb_noun")?;
        payload.description = normalize_optional_text(payload.description);
        repo::create_task(&self.db, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn list_tasks(&self, page: i64, page_size: i64) -> Result<Page<Task>, ServiceError> {
        repo::list_tasks(&self.db, page, page_size)
            .await
            .map_err(Into::into)
    }

    pub async fn get_task(&self, id: TaskId) -> Result<Task, ServiceError> {
        self.task_or_not_found(id).await
    }

    pub async fn update_task(&self, id: TaskId, payload: TaskUpdate) -> Result<Task, ServiceError> {
        let mut task = self.task_or_not_found(id).await?;

        if let Some(verb_noun) = payload.verb_noun {
            task.verb_noun = normalize_title(verb_noun, "verb_noun")?;
        }
        if let Some(project_id) = payload.project_id {
            task.project_id = project_id;
        }
        if let Some(description) = payload.description {
            task.description = normalize_optional_text(Some(description));
        }
        if let Some(in_inbox) = payload.in_inbox {
            task.in_inbox = in_inbox;
        }
        if let Some(when_bucket) = payload.when_bucket {
            task.when_bucket = when_bucket;
        }
        if let Some(block_type) = payload.block_type {
            task.block_type = block_type;
        }
        if let Some(duration_minutes) = payload.duration_minutes {
            task.duration_minutes = duration_minutes.filter(|value| *value > 0);
        }
        if let Some(priority) = payload.priority {
            task.priority = priority;
        }
        if let Some(frog) = payload.frog {
            task.frog = frog;
        }
        if let Some(alignment) = payload.alignment {
            task.alignment = alignment;
        }
        if let Some(first_action) = payload.first_action {
            task.first_action = normalize_optional_text(Some(first_action));
        }
        if let Some(scheduled_for) = payload.scheduled_for {
            task.scheduled_for = scheduled_for;
        }
        if let Some(status) = payload.status {
            match status {
                TaskStatus::Done => apply_complete(&mut task),
                TaskStatus::Archived => apply_archive(&mut task),
                TaskStatus::Pending => apply_reopen(&mut task),
                other => task.status = other,
            }
        }
        if let Some(owner_type) = payload.owner_type {
            task.owner_type = owner_type;
        }

        repo::update_task(&self.db, &task).await.map_err(Into::into)
    }

    pub async fn delete_task(&self, id: TaskId) -> Result<(), ServiceError> {
        if repo::delete_task(&self.db, id).await? {
            Ok(())
        } else {
            Err(ServiceError::NotFound { entity: "task" })
        }
    }

    pub async fn complete_task(&self, id: TaskId) -> Result<Task, ServiceError> {
        let mut task = self.task_or_not_found(id).await?;
        apply_complete(&mut task);
        repo::update_task(&self.db, &task).await.map_err(Into::into)
    }

    pub async fn reopen_task(&self, id: TaskId) -> Result<Task, ServiceError> {
        let mut task = self.task_or_not_found(id).await?;
        apply_reopen(&mut task);
        repo::update_task(&self.db, &task).await.map_err(Into::into)
    }

    pub async fn archive_task(&self, id: TaskId) -> Result<Task, ServiceError> {
        let mut task = self.task_or_not_found(id).await?;
        apply_archive(&mut task);
        repo::update_task(&self.db, &task).await.map_err(Into::into)
    }

    pub async fn restore_task(&self, id: TaskId) -> Result<Task, ServiceError> {
        let mut task = self.task_or_not_found(id).await?;
        apply_restore(&mut task);
        repo::update_task(&self.db, &task).await.map_err(Into::into)
    }

    pub async fn quick_capture(&self, payload: QuickCapture) -> Result<Task, ServiceError> {
        self.create_task(TaskCreate {
            verb_noun: payload.verb_noun,
            project_id: None,
            description: payload.description,
            in_inbox: true,
            when_bucket: WhenBucket::Later,
            block_type: None,
            duration_minutes: None,
            priority: None,
            frog: false,
            alignment: None,
            first_action: None,
            scheduled_for: None,
            owner_type: Default::default(),
        })
        .await
    }

    async fn project_or_not_found(&self, id: ProjectId) -> Result<Project, ServiceError> {
        repo::get_project(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "project" })
    }

    async fn task_or_not_found(&self, id: TaskId) -> Result<Task, ServiceError> {
        repo::get_task(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound { entity: "task" })
    }
}

async fn ensure_weekly_cap(
    pool: &sqlx::SqlitePool,
    category: ProjectCategory,
    make_active: bool,
) -> Result<(), ServiceError> {
    if !make_active {
        return Ok(());
    }

    let current = repo::count_active_projects_by_category(pool, category).await?;
    let cap = category.weekly_cap();
    if current >= cap {
        return Err(ServiceError::WeeklyCap {
            category,
            current,
            cap,
        });
    }

    Ok(())
}

fn normalize_title(value: String, field: &'static str) -> Result<String, ServiceError> {
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

fn normalize_success_pack(payload: SuccessPackUpdate) -> SuccessPackUpdate {
    SuccessPackUpdate {
        guides: normalize_optional_text(payload.guides),
        peers: normalize_optional_text(payload.peers),
        supporters: normalize_optional_text(payload.supporters),
        beneficiaries: normalize_optional_text(payload.beneficiaries),
    }
}

fn project_title_looks_action(title: &str) -> bool {
    let words = title
        .split(|character: char| {
            !(character.is_ascii_alphabetic()
                || character == '\''
                || character == '/'
                || character == '-')
        })
        .filter(|word| !word.is_empty())
        .map(str::to_ascii_lowercase)
        .collect::<Vec<_>>();
    let Some(first) = words.first() else {
        return false;
    };
    if words.len() < 2 {
        return false;
    }
    ACTION_STARTERS.contains(&first.as_str())
        || (first.len() >= 5
            && (first.ends_with("ize")
                || first.ends_with("ise")
                || first.ends_with("ify")
                || first.ends_with("ate")
                || first.ends_with("en")))
}

const ACTION_STARTERS: &[&str] = &[
    "add", "align", "audit", "book", "build", "call", "clean", "clear", "close", "coach",
    "complete", "create", "cut", "define", "deliver", "design", "draft", "edit", "finish", "fix",
    "improve", "launch", "learn", "make", "map", "move", "organize", "organise", "plan", "prepare",
    "publish", "record", "reduce", "refine", "release", "remove", "repair", "replace", "research",
    "reset", "review", "schedule", "ship", "simplify", "sort", "start", "train", "update", "write",
];

fn reset_to_unprocessed_inbox(task: &mut Task) {
    task.in_inbox = true;
    task.archived_from_inbox = false;
    task.status = TaskStatus::Pending;
    task.when_bucket = WhenBucket::Later;
    task.completed_at = None;
    task.intake_intent = INBOX_INTENT_UNPROCESSED.to_string();
    task.intake_container = INBOX_INTENT_UNPROCESSED.to_string();
    task.intake_processed_at = None;
}

fn apply_complete(task: &mut Task) {
    task.status = TaskStatus::Done;
    task.completed_at = Some(Utc::now());
    task.in_inbox = false;
}

fn apply_reopen(task: &mut Task) {
    task.status = TaskStatus::Pending;
    task.completed_at = None;
}

fn apply_archive(task: &mut Task) {
    task.status = TaskStatus::Archived;
    task.in_inbox = false;
    task.archived_from_inbox = false;
}

fn apply_restore(task: &mut Task) {
    task.status = TaskStatus::Pending;
    task.completed_at = None;
    if task.archived_from_inbox {
        reset_to_unprocessed_inbox(task);
    } else {
        task.in_inbox = false;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;
    use sfo_core::{
        ProjectCardUpdate, ProjectCategory, ProjectChunkCreate, ProjectStatus, SuccessPackUpdate,
        TaskStatus,
    };
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn service() -> PlanningService {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        PlanningService::new(pool)
    }

    fn project_payload(title: &str, category: ProjectCategory, active: bool) -> ProjectCreate {
        ProjectCreate {
            title: title.to_string(),
            description: None,
            category,
            size: None,
            time_horizon: None,
            start_date: None,
            target_date: None,
            level_of_success: None,
            why_link_text: None,
            drag_points_notes: None,
            gates_notes: None,
            budget_notes: None,
            active_this_week: active,
        }
    }

    #[tokio::test]
    async fn create_project_enforces_work_weekly_cap() {
        let service = service().await;
        for index in 0..4 {
            service
                .create_project(project_payload(
                    &format!("Work {index}"),
                    ProjectCategory::Work,
                    true,
                ))
                .await
                .expect("create active work project");
        }

        let error = service
            .create_project(project_payload("Overflow", ProjectCategory::Work, true))
            .await
            .expect_err("weekly cap error");

        assert!(matches!(error, ServiceError::WeeklyCap { cap: 4, .. }));
    }

    #[tokio::test]
    async fn task_lifecycle_updates_status_and_completion_state() {
        let service = service().await;
        let task = service
            .quick_capture(QuickCapture {
                verb_noun: "Capture this".to_string(),
                description: None,
            })
            .await
            .expect("quick capture");

        assert!(task.in_inbox);
        assert_eq!(task.when_bucket, WhenBucket::Later);

        let completed = service.complete_task(task.id).await.expect("complete task");
        assert_eq!(completed.status, TaskStatus::Done);
        assert!(!completed.in_inbox);
        assert!(completed.completed_at.is_some());

        let reopened = service.reopen_task(task.id).await.expect("reopen task");
        assert_eq!(reopened.status, TaskStatus::Pending);
        assert!(reopened.completed_at.is_none());

        let archived = service.archive_task(task.id).await.expect("archive task");
        assert_eq!(archived.status, TaskStatus::Archived);
        assert!(!archived.in_inbox);

        let restored = service.restore_task(task.id).await.expect("restore task");
        assert_eq!(restored.status, TaskStatus::Pending);
    }

    #[tokio::test]
    async fn save_project_card_requires_target_date() {
        let service = service().await;
        let project = service
            .create_project(project_payload(
                "Plan roadmap",
                ProjectCategory::Work,
                false,
            ))
            .await
            .expect("project");

        let error = service
            .save_project_card(
                project.id,
                ProjectCardUpdate {
                    title: "Plan roadmap".to_string(),
                    description: None,
                    status: ProjectStatus::Active,
                    category: ProjectCategory::Work,
                    size: None,
                    time_horizon: Some("quarter".to_string()),
                    start_date: None,
                    target_date: None,
                    level_of_success: None,
                    why_link_text: None,
                    drag_points_notes: None,
                    gates_notes: None,
                    budget_notes: None,
                    active_this_week: false,
                    verb_check_ack: true,
                    success_pack: None,
                },
            )
            .await
            .expect_err("target date validation");

        assert!(matches!(
            error,
            ServiceError::Validation {
                field: "target_date",
                ..
            }
        ));
    }

    #[tokio::test]
    async fn save_project_card_normalizes_fields_and_success_pack() {
        let service = service().await;
        let project = service
            .create_project(project_payload(
                "Plan roadmap",
                ProjectCategory::Work,
                false,
            ))
            .await
            .expect("project");

        let card = service
            .save_project_card(
                project.id,
                ProjectCardUpdate {
                    title: "  Plan annual roadmap  ".to_string(),
                    description: Some("  ".to_string()),
                    status: ProjectStatus::Active,
                    category: ProjectCategory::Personal,
                    size: None,
                    time_horizon: Some(" quarter ".to_string()),
                    start_date: Some(NaiveDate::from_ymd_opt(2026, 5, 15).unwrap()),
                    target_date: Some(NaiveDate::from_ymd_opt(2026, 8, 1).unwrap()),
                    level_of_success: None,
                    why_link_text: Some("  Calmer month  ".to_string()),
                    drag_points_notes: Some("  Too many commitments  ".to_string()),
                    gates_notes: Some("  Use planning strengths  ".to_string()),
                    budget_notes: Some("  Two focus blocks  ".to_string()),
                    active_this_week: false,
                    verb_check_ack: false,
                    success_pack: Some(SuccessPackUpdate {
                        guides: Some("  Charlie  ".to_string()),
                        peers: Some(" ".to_string()),
                        supporters: None,
                        beneficiaries: Some("Family".to_string()),
                    }),
                },
            )
            .await
            .expect("save project card");

        assert_eq!(card.project.title, "Plan annual roadmap");
        assert!(card.project.description.is_none());
        assert_eq!(card.project.time_horizon.as_deref(), Some("quarter"));
        assert_eq!(card.project.why_link_text.as_deref(), Some("Calmer month"));
        let success_pack = card.success_pack.expect("success pack");
        assert_eq!(success_pack.guides.as_deref(), Some("Charlie"));
        assert!(success_pack.peers.is_none());
        assert_eq!(success_pack.beneficiaries.as_deref(), Some("Family"));
    }

    #[tokio::test]
    async fn create_project_chunk_links_week_task_to_project() {
        let service = service().await;
        let project = service
            .create_project(project_payload(
                "Plan roadmap",
                ProjectCategory::Work,
                false,
            ))
            .await
            .expect("project");

        let chunk = service
            .create_project_chunk(
                project.id,
                ProjectChunkCreate {
                    verb_noun: "  Draft roadmap  ".to_string(),
                    description: Some("  Starter chunk  ".to_string()),
                    when_bucket: WhenBucket::Week,
                    block_type: None,
                    duration_minutes: Some(30),
                    frog: true,
                },
            )
            .await
            .expect("chunk");

        assert_eq!(chunk.project_id, Some(project.id));
        assert_eq!(chunk.verb_noun, "Draft roadmap");
        assert_eq!(chunk.description.as_deref(), Some("Starter chunk"));
        assert_eq!(chunk.when_bucket, WhenBucket::Week);
        assert!(chunk.frog);
    }
}
