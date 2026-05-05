use sfo_core::ProjectCategory;

#[derive(Debug, thiserror::Error)]
pub enum ServiceError {
    #[error(transparent)]
    Db(#[from] sfo_db::DbError),
    #[error("{entity} not found")]
    NotFound { entity: &'static str },
    #[error("Weekly cap reached for {category:?} projects ({current}/{cap})")]
    WeeklyCap {
        category: ProjectCategory,
        current: i64,
        cap: i64,
    },
    #[error("invalid {field}: {message}")]
    Validation {
        field: &'static str,
        message: &'static str,
    },
}
