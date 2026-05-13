use chrono::{Duration, Utc};
use sfo_core::{
    CaptureHorizon, GuidedCaptureKind, GuidedCaptureRequest, GuidedCaptureResponse,
    GuidedInboxIntent, OwnerType, ProjectChunkCreate, ProjectCreate, Task, TaskCreate, TaskId,
    TaskStatus, WaitingOnCreate, WhenBucket, INBOX_INTENT_SUPPORT_PROJECT,
    INBOX_INTENT_UNPROCESSED,
};
use sfo_db::planning as planning_repo;

use crate::{PlanningService, ServiceError, WaitingService};

const PROJECT_DATE_REQUIRED: &str = "Set a target date for this project. No date = no finish.";
const PROJECT_VERB_REQUIRED: &str =
    "Project title should start with an action verb (e.g. Move Sam to Atlanta).";

#[derive(Clone)]
pub struct CaptureService {
    db: sqlx::SqlitePool,
}

impl CaptureService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn submit_guided(
        &self,
        payload: GuidedCaptureRequest,
    ) -> Result<GuidedCaptureResponse, ServiceError> {
        let title = normalize_title(&payload.capture_text, "capture_text")?;
        let source_task = self.load_active_source_task(payload.source_task_id).await?;
        let description = normalize_description(payload.description.clone(), source_task.as_ref());
        let inbox_intent = if source_task.is_some() {
            payload.inbox_intent.ok_or(ServiceError::Validation {
                field: "inbox_intent",
                message: "Choose how to handle this inbox item before saving.",
            })?
        } else {
            GuidedInboxIntent::SupportProject
        };

        if inbox_intent.is_quick_route() {
            let mut task = source_task.ok_or(ServiceError::Validation {
                field: "source_task_id",
                message: "quick routing requires an inbox source item",
            })?;
            task.verb_noun = title;
            task.description = description;
            apply_inbox_container(&mut task, inbox_intent);
            let task = planning_repo::update_task(&self.db, &task).await?;
            return Ok(GuidedCaptureResponse {
                message: "Saved to container".to_string(),
                task: None,
                project: None,
                source_task: Some(task),
            });
        }

        if matches!(
            payload.item_kind,
            GuidedCaptureKind::Task | GuidedCaptureKind::Project
        ) && !payload.displacement_ack
        {
            return Err(ServiceError::Validation {
                field: "displacement_ack",
                message: "Confirm the displacement check before saving.",
            });
        }

        if source_task.is_some()
            && payload.item_kind == GuidedCaptureKind::Task
            && payload.project_id.is_none()
        {
            return Err(ServiceError::Validation {
                field: "project_id",
                message: "Select an existing project or choose Project flow.",
            });
        }

        match payload.item_kind {
            GuidedCaptureKind::DecideLater => {
                self.capture_decide_later(title, description, source_task, payload.owner_type)
                    .await
            }
            GuidedCaptureKind::Project => {
                self.capture_project(title, description, source_task, payload)
                    .await
            }
            GuidedCaptureKind::Task => {
                self.capture_task(title, description, source_task, payload)
                    .await
            }
        }
    }

    async fn capture_decide_later(
        &self,
        title: String,
        description: Option<String>,
        source_task: Option<Task>,
        owner_type: sfo_core::OwnerType,
    ) -> Result<GuidedCaptureResponse, ServiceError> {
        if let Some(mut task) = source_task {
            task.verb_noun = title;
            task.description = description;
            reset_to_unprocessed_inbox(&mut task);
            let task = planning_repo::update_task(&self.db, &task).await?;
            return Ok(GuidedCaptureResponse {
                message: "Captured".to_string(),
                task: None,
                project: None,
                source_task: Some(task),
            });
        }

        let task = PlanningService::new(self.db.clone())
            .create_task(TaskCreate {
                verb_noun: title,
                project_id: None,
                description,
                in_inbox: true,
                when_bucket: WhenBucket::Later,
                block_type: None,
                duration_minutes: None,
                priority: None,
                frog: false,
                alignment: None,
                first_action: None,
                scheduled_for: None,
                owner_type,
            })
            .await?;

        Ok(GuidedCaptureResponse {
            message: "Captured".to_string(),
            task: Some(task),
            project: None,
            source_task: None,
        })
    }

    async fn capture_project(
        &self,
        title: String,
        description: Option<String>,
        source_task: Option<Task>,
        payload: GuidedCaptureRequest,
    ) -> Result<GuidedCaptureResponse, ServiceError> {
        let target_date = payload.target_date.ok_or(ServiceError::Validation {
            field: "target_date",
            message: PROJECT_DATE_REQUIRED,
        })?;
        if !project_title_looks_action(&title) && !payload.verb_check_ack {
            return Err(ServiceError::Validation {
                field: "capture_text",
                message: PROJECT_VERB_REQUIRED,
            });
        }

        let project = PlanningService::new(self.db.clone())
            .create_project(ProjectCreate {
                title,
                description,
                category: payload.category,
                size: None,
                time_horizon: Some(payload.horizon.project_horizon().to_string()),
                start_date: None,
                target_date: Some(target_date),
                level_of_success: payload.level_of_success,
                why_link_text: compose_why_text(payload.why_link_text, payload.why_tags),
                drag_points_notes: None,
                gates_notes: None,
                budget_notes: None,
                active_this_week: payload.include_this_week
                    || payload.horizon == CaptureHorizon::Week,
            })
            .await?;

        let chunk = if let Some(first_chunk) = normalize_optional_text(payload.first_chunk) {
            Some(
                PlanningService::new(self.db.clone())
                    .create_project_chunk(
                        project.id,
                        ProjectChunkCreate {
                            verb_noun: first_chunk,
                            description: None,
                            when_bucket: payload.horizon.task_when_bucket(),
                            block_type: None,
                            duration_minutes: None,
                            frog: false,
                        },
                    )
                    .await?,
            )
        } else {
            None
        };

        let source_task = if let Some(mut task) = source_task {
            mark_support_project_processed(&mut task);
            task.in_inbox = false;
            task.archived_from_inbox = true;
            task.status = TaskStatus::Archived;
            Some(planning_repo::update_task(&self.db, &task).await?)
        } else {
            None
        };

        Ok(GuidedCaptureResponse {
            message: "Captured".to_string(),
            task: chunk,
            project: Some(project),
            source_task,
        })
    }

    async fn capture_task(
        &self,
        title: String,
        description: Option<String>,
        source_task: Option<Task>,
        payload: GuidedCaptureRequest,
    ) -> Result<GuidedCaptureResponse, ServiceError> {
        let when_bucket = payload.horizon.task_when_bucket();
        let duration_minutes = payload.duration_minutes.filter(|value| *value > 0);
        let resurface_on = compute_resurface_on(when_bucket);

        let task = if let Some(mut task) = source_task {
            task.verb_noun = title;
            task.project_id = payload.project_id;
            task.description = description;
            task.in_inbox = false;
            task.archived_from_inbox = false;
            task.when_bucket = when_bucket;
            task.block_type = payload.block_type;
            task.duration_minutes = duration_minutes;
            task.frog = payload.frog;
            task.owner_type = payload.owner_type;
            task.alignment = None;
            task.resurface_on = resurface_on;
            task.status = TaskStatus::Pending;
            task.completed_at = None;
            mark_support_project_processed(&mut task);
            planning_repo::update_task(&self.db, &task).await?
        } else {
            let mut task = PlanningService::new(self.db.clone())
                .create_task(TaskCreate {
                    verb_noun: title,
                    project_id: payload.project_id,
                    description,
                    in_inbox: false,
                    when_bucket,
                    block_type: payload.block_type,
                    duration_minutes,
                    priority: None,
                    frog: payload.frog,
                    alignment: None,
                    first_action: None,
                    scheduled_for: None,
                    owner_type: payload.owner_type,
                })
                .await?;
            task.resurface_on = resurface_on;
            planning_repo::update_task(&self.db, &task).await?
        };
        if task.owner_type == OwnerType::Opp {
            self.create_waiting_for_opp(&task, payload.waiting_person)
                .await?;
        }

        Ok(GuidedCaptureResponse {
            message: "Captured".to_string(),
            task: Some(task),
            project: None,
            source_task: None,
        })
    }

    async fn load_active_source_task(
        &self,
        id: Option<TaskId>,
    ) -> Result<Option<Task>, ServiceError> {
        let Some(id) = id else {
            return Ok(None);
        };
        let task = planning_repo::get_task(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound {
                entity: "inbox item",
            })?;
        if !task.in_inbox || !matches!(task.status, TaskStatus::Pending | TaskStatus::InProgress) {
            return Err(ServiceError::NotFound {
                entity: "inbox item",
            });
        }
        Ok(Some(task))
    }

    async fn create_waiting_for_opp(
        &self,
        task: &Task,
        person: Option<String>,
    ) -> Result<(), ServiceError> {
        WaitingService::new(self.db.clone())
            .create_waiting_on(WaitingOnCreate {
                description: task.verb_noun.clone(),
                person,
                project_id: task.project_id,
                last_followup: None,
            })
            .await?;
        Ok(())
    }
}

fn normalize_title(value: &str, field: &'static str) -> Result<String, ServiceError> {
    let cleaned = value.trim().to_string();
    if cleaned.is_empty() {
        return Err(ServiceError::Validation {
            field,
            message: "must not be empty",
        });
    }
    Ok(cleaned)
}

fn normalize_description(value: Option<String>, source_task: Option<&Task>) -> Option<String> {
    value
        .and_then(|text| {
            let cleaned = text.trim().to_string();
            if cleaned.is_empty() {
                None
            } else {
                Some(cleaned)
            }
        })
        .or_else(|| source_task.and_then(|task| task.description.clone()))
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

fn apply_inbox_container(task: &mut Task, intent: GuidedInboxIntent) {
    let intent = intent.as_str().to_string();
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
    task.intake_intent = INBOX_INTENT_UNPROCESSED.to_string();
    task.intake_container = INBOX_INTENT_UNPROCESSED.to_string();
    task.intake_processed_at = None;
}

fn mark_support_project_processed(task: &mut Task) {
    task.intake_intent = INBOX_INTENT_SUPPORT_PROJECT.to_string();
    task.intake_container = INBOX_INTENT_SUPPORT_PROJECT.to_string();
    task.intake_processed_at = Some(Utc::now());
}

fn compute_resurface_on(when_bucket: WhenBucket) -> Option<chrono::NaiveDate> {
    let today = Utc::now().date_naive();
    match when_bucket {
        WhenBucket::Today | WhenBucket::Week => None,
        WhenBucket::Month => Some(today + Duration::days(7)),
        WhenBucket::Quarter => Some(today + Duration::days(14)),
        WhenBucket::Later => Some(today + Duration::days(30)),
    }
}

fn compose_why_text(free_text: Option<String>, tags: Vec<String>) -> Option<String> {
    let free_text = free_text.and_then(|text| {
        let cleaned = text.trim().to_string();
        if cleaned.is_empty() {
            None
        } else {
            Some(cleaned)
        }
    });
    let tag_values = tags
        .into_iter()
        .map(|tag| tag.trim().to_string())
        .filter(|tag| !tag.is_empty())
        .collect::<Vec<_>>();
    let tag_text = if tag_values.is_empty() {
        None
    } else {
        Some(format!("Tags: {}", tag_values.join(", ")))
    };
    match (free_text, tag_text) {
        (Some(free), Some(tags)) => Some(format!("{free}\n{tags}")),
        (Some(free), None) => Some(free),
        (None, Some(tags)) => Some(tags),
        (None, None) => None,
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

#[cfg(test)]
mod tests {
    use super::*;
    use sfo_core::{QuickCapture, INBOX_INTENT_LEARN_EXPLORE};
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn services() -> (PlanningService, CaptureService) {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        (
            PlanningService::new(pool.clone()),
            CaptureService::new(pool),
        )
    }

    #[tokio::test]
    async fn guided_capture_routes_source_to_learning() {
        let (planning, capture) = services().await;
        let source = planning
            .quick_capture(QuickCapture {
                verb_noun: "Inbox source".to_string(),
                description: None,
            })
            .await
            .expect("quick capture");

        let response = capture
            .submit_guided(GuidedCaptureRequest {
                capture_text: "Read this later".to_string(),
                description: None,
                item_kind: GuidedCaptureKind::Task,
                inbox_intent: Some(GuidedInboxIntent::LearnExplore),
                displacement_ack: false,
                source_task_id: Some(source.id),
                category: Default::default(),
                project_id: None,
                horizon: Default::default(),
                include_this_week: true,
                target_date: None,
                verb_check_ack: false,
                level_of_success: None,
                why_link_text: None,
                why_tags: vec![],
                first_chunk: None,
                block_type: None,
                duration_minutes: None,
                frog: false,
                owner_type: Default::default(),
                waiting_person: None,
            })
            .await
            .expect("guided capture");

        let task = response.source_task.expect("source task");
        assert_eq!(task.verb_noun, "Read this later");
        assert!(!task.in_inbox);
        assert_eq!(task.intake_container, INBOX_INTENT_LEARN_EXPLORE);
    }

    #[tokio::test]
    async fn guided_capture_requires_project_for_source_support_task() {
        let (planning, capture) = services().await;
        let source = planning
            .quick_capture(QuickCapture {
                verb_noun: "Inbox source".to_string(),
                description: None,
            })
            .await
            .expect("quick capture");

        let error = capture
            .submit_guided(GuidedCaptureRequest {
                capture_text: "Action this".to_string(),
                description: None,
                item_kind: GuidedCaptureKind::Task,
                inbox_intent: Some(GuidedInboxIntent::SupportProject),
                displacement_ack: true,
                source_task_id: Some(source.id),
                category: Default::default(),
                project_id: None,
                horizon: Default::default(),
                include_this_week: true,
                target_date: None,
                verb_check_ack: false,
                level_of_success: None,
                why_link_text: None,
                why_tags: vec![],
                first_chunk: None,
                block_type: None,
                duration_minutes: None,
                frog: false,
                owner_type: Default::default(),
                waiting_person: None,
            })
            .await
            .expect_err("validation error");

        assert!(matches!(
            error,
            ServiceError::Validation {
                field: "project_id",
                ..
            }
        ));
    }

    #[test]
    fn project_title_validation_matches_action_titles() {
        assert!(project_title_looks_action("Plan annual roadmap"));
        assert!(!project_title_looks_action("Website redesign"));
    }
}
