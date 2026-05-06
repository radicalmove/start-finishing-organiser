pub mod auth;
pub mod config;
pub mod error;
pub mod routes;
pub mod state;

use axum::middleware;
use axum::{
    http::{header, HeaderValue, Method, StatusCode},
    routing::get,
    Router,
};
use tower_http::{
    cors::{AllowOrigin, CorsLayer},
    trace::TraceLayer,
};

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
        .layer(cors_layer())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

fn cors_layer() -> CorsLayer {
    CorsLayer::new()
        .allow_origin(AllowOrigin::list([
            HeaderValue::from_static("tauri://localhost"),
            HeaderValue::from_static("https://tauri.localhost"),
        ]))
        .allow_methods([Method::GET, Method::POST, Method::PATCH, Method::DELETE])
        .allow_headers([header::AUTHORIZATION, header::CONTENT_TYPE, header::ACCEPT])
}
