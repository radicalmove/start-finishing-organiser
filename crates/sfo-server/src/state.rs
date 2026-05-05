#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::SqlitePool,
}

impl AppState {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self { db }
    }
}
