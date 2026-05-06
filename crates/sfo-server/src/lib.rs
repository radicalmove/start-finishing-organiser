pub mod auth;
pub mod config;
pub mod error;
pub mod routes;
pub mod state;

use axum::middleware;
use axum::{http::StatusCode, routing::get, Router};
use tower_http::trace::TraceLayer;

pub use state::AppState;

pub fn build_router(state: AppState) -> Router {
    let api_router = routes::api::router()
        .fallback(|| async { StatusCode::NOT_FOUND })
        .layer(middleware::from_fn_with_state(
            state.clone(),
            auth::require_api_token,
        ));

    Router::new()
        .route("/healthz", get(routes::health::healthz))
        .nest("/api/v1", api_router)
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
