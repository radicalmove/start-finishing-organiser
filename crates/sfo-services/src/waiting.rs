use sfo_core::{Page, WaitingId, WaitingOn, WaitingOnCreate, WaitingOnUpdate};
use sfo_db::waiting as repo;

use crate::ServiceError;

#[derive(Clone)]
pub struct WaitingService {
    db: sqlx::SqlitePool,
}

impl WaitingService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn create_waiting_on(
        &self,
        mut payload: WaitingOnCreate,
    ) -> Result<WaitingOn, ServiceError> {
        payload.description = normalize_required_text(payload.description, "description")?;
        payload.person = normalize_optional_text(payload.person);
        repo::create_waiting_on(&self.db, payload)
            .await
            .map_err(Into::into)
    }

    pub async fn list_waiting_on(
        &self,
        page: i64,
        page_size: i64,
    ) -> Result<Page<WaitingOn>, ServiceError> {
        repo::list_waiting_on(&self.db, page, page_size)
            .await
            .map_err(Into::into)
    }

    pub async fn update_waiting_on(
        &self,
        id: WaitingId,
        payload: WaitingOnUpdate,
    ) -> Result<WaitingOn, ServiceError> {
        let mut item = self.waiting_or_not_found(id).await?;
        if let Some(description) = payload.description {
            item.description = normalize_required_text(description, "description")?;
        }
        if let Some(person) = payload.person {
            item.person = normalize_optional_text(person);
        }
        if let Some(project_id) = payload.project_id {
            item.project_id = project_id;
        }
        if let Some(last_followup) = payload.last_followup {
            item.last_followup = last_followup;
        }

        repo::update_waiting_on(&self.db, &item)
            .await
            .map_err(Into::into)
    }

    pub async fn resolve_waiting_on(&self, id: WaitingId) -> Result<(), ServiceError> {
        if repo::delete_waiting_on(&self.db, id).await? {
            Ok(())
        } else {
            Err(ServiceError::NotFound {
                entity: "waiting item",
            })
        }
    }

    async fn waiting_or_not_found(&self, id: WaitingId) -> Result<WaitingOn, ServiceError> {
        repo::get_waiting_on(&self.db, id)
            .await?
            .ok_or(ServiceError::NotFound {
                entity: "waiting item",
            })
    }
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
    use sfo_db::{connect, run_migrations, DbConfig};

    async fn service() -> WaitingService {
        let pool = connect(&DbConfig::new("sqlite::memory:"))
            .await
            .expect("connect");
        run_migrations(&pool).await.expect("migrate");
        WaitingService::new(pool)
    }

    #[tokio::test]
    async fn service_creates_and_resolves_waiting_item() {
        let service = service().await;
        let item = service
            .create_waiting_on(WaitingOnCreate {
                description: " Waiting on Sam ".to_string(),
                person: Some(" Sam ".to_string()),
                project_id: None,
                last_followup: None,
            })
            .await
            .expect("create waiting");

        assert_eq!(item.description, "Waiting on Sam");
        assert_eq!(item.person.as_deref(), Some("Sam"));

        service
            .resolve_waiting_on(item.id)
            .await
            .expect("resolve waiting");
        let page = service.list_waiting_on(1, 10).await.expect("list waiting");
        assert_eq!(page.total, 0);
    }
}
