#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ServerConfig {
    pub bind_addr: String,
    pub database_url: String,
    pub api_token: Option<String>,
}

impl ServerConfig {
    #[must_use]
    pub fn from_env() -> Self {
        Self {
            bind_addr: std::env::var("SFO_RUST_BIND")
                .unwrap_or_else(|_| "127.0.0.1:8088".to_string()),
            database_url: std::env::var("SFO_RUST_DATABASE_URL")
                .unwrap_or_else(|_| "sqlite://sfo-rust.db".to_string()),
            api_token: env_optional("SFO_RUST_API_TOKEN"),
        }
    }
}

fn env_optional(key: &str) -> Option<String> {
    std::env::var(key)
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
}
