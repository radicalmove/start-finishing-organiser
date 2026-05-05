pub mod backup;
pub mod config;
pub mod error;
pub mod import;
pub mod planning;

use sqlx::sqlite::{SqliteConnectOptions, SqliteJournalMode, SqlitePoolOptions};
use std::str::FromStr;

pub use config::DbConfig;
pub use error::DbError;

pub async fn connect(config: &DbConfig) -> Result<sqlx::SqlitePool, DbError> {
    let is_memory = config.database_url.contains(":memory:");
    let mut options = SqliteConnectOptions::from_str(&config.database_url)?
        .create_if_missing(true)
        .foreign_keys(true);

    if !is_memory {
        options = options.journal_mode(SqliteJournalMode::Wal);
    }

    let pool = SqlitePoolOptions::new()
        .max_connections(if is_memory { 1 } else { 5 })
        .connect_with(options)
        .await?;

    sqlx::query("PRAGMA busy_timeout = 5000")
        .execute(&pool)
        .await?;

    Ok(pool)
}

pub async fn run_migrations(pool: &sqlx::SqlitePool) -> Result<(), DbError> {
    sqlx::migrate!("./migrations").run(pool).await?;
    Ok(())
}

pub async fn health_check(pool: &sqlx::SqlitePool) -> Result<(), DbError> {
    sqlx::query("SELECT 1").execute(pool).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn migrations_create_app_metadata() {
        let config = DbConfig::new("sqlite::memory:");
        let pool = connect(&config).await.expect("connect");
        run_migrations(&pool).await.expect("migrate");

        let value: String =
            sqlx::query_scalar("SELECT value FROM app_metadata WHERE key = 'schema'")
                .fetch_one(&pool)
                .await
                .expect("schema metadata row");

        assert_eq!(value, "sfo-rust-foundation");
    }

    #[tokio::test]
    async fn health_check_runs_simple_query() {
        let config = DbConfig::new("sqlite::memory:");
        let pool = connect(&config).await.expect("connect");
        health_check(&pool).await.expect("healthy database");
    }
}
