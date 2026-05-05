use sfo_db::{connect, run_migrations, DbConfig};
use sfo_server::config::ServerConfig;
use sfo_server::{build_router, AppState};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| "sfo_server=info,tower_http=info".into());

    tracing_subscriber::fmt().with_env_filter(filter).init();

    let config = ServerConfig::from_env();
    let db = connect(&DbConfig::new(config.database_url)).await?;
    run_migrations(&db).await?;

    let listener = tokio::net::TcpListener::bind(&config.bind_addr).await?;
    tracing::info!(bind_addr = %config.bind_addr, "starting SFO Rust server");

    axum::serve(listener, build_router(AppState::new(db))).await?;
    Ok(())
}
