#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ServerConfig {
    pub bind_addr: String,
    pub database_url: String,
}

impl ServerConfig {
    #[must_use]
    pub fn from_env() -> Self {
        Self {
            bind_addr: std::env::var("SFO_RUST_BIND")
                .unwrap_or_else(|_| "127.0.0.1:8088".to_string()),
            database_url: std::env::var("SFO_RUST_DATABASE_URL")
                .unwrap_or_else(|_| "sqlite://sfo-rust.db".to_string()),
        }
    }
}
