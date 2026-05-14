use sfo_core::GlobalSearchResults;
use sfo_db::search as repo;

use crate::ServiceError;

#[derive(Clone)]
pub struct SearchService {
    db: sqlx::SqlitePool,
}

impl SearchService {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }

    pub async fn global_search(
        &self,
        query: &str,
        include_recycle_bin: bool,
    ) -> Result<GlobalSearchResults, ServiceError> {
        repo::global_search(&self.db, query, include_recycle_bin)
            .await
            .map_err(Into::into)
    }
}
