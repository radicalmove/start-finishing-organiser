#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::SqlitePool,
    api_token: Option<String>,
}

impl AppState {
    #[must_use]
    pub fn new(db: sqlx::SqlitePool) -> Self {
        Self {
            db,
            api_token: None,
        }
    }

    #[must_use]
    pub fn with_api_token(mut self, token: impl Into<String>) -> Self {
        let token = token.into();
        self.api_token = if token.trim().is_empty() {
            None
        } else {
            Some(token)
        };
        self
    }

    #[must_use]
    pub fn api_token(&self) -> Option<&str> {
        self.api_token.as_deref()
    }

    #[must_use]
    pub fn auth_required(&self) -> bool {
        self.api_token.is_some()
    }
}
