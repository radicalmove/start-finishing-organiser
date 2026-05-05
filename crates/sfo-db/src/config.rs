#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DbConfig {
    pub database_url: String,
}

impl DbConfig {
    #[must_use]
    pub fn new(database_url: impl Into<String>) -> Self {
        Self {
            database_url: database_url.into(),
        }
    }
}
