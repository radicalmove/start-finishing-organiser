pub mod config;
pub mod error;
pub mod routes;
pub mod state;

use axum::{routing::get, Router};
use tower_http::trace::TraceLayer;

pub use state::AppState;

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/healthz", get(routes::health::healthz))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
