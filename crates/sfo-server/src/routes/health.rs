use axum::extract::State;
use axum::Json;
use serde::Serialize;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub database: &'static str,
}

pub async fn healthz(State(state): State<AppState>) -> Json<HealthResponse> {
    let database = if sfo_db::health_check(&state.db).await.is_ok() {
        "ok"
    } else {
        "error"
    };

    Json(HealthResponse {
        status: if database == "ok" { "ok" } else { "degraded" },
        database,
    })
}
