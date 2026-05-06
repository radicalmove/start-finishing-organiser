use axum::body::Body;
use axum::extract::State;
use axum::http::{header, Request, StatusCode};
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Serialize;

use crate::AppState;

#[derive(Debug, Serialize)]
struct AuthErrorBody {
    detail: &'static str,
}

pub async fn require_api_token(
    State(state): State<AppState>,
    request: Request<Body>,
    next: Next,
) -> Response {
    if is_public_api_path(request.uri().path()) || token_is_valid(&state, &request) {
        return next.run(request).await;
    }

    (
        StatusCode::UNAUTHORIZED,
        Json(AuthErrorBody {
            detail: "missing or invalid API token",
        }),
    )
        .into_response()
}

fn is_public_api_path(path: &str) -> bool {
    path == "/api/v1/auth/status" || path == "/auth/status"
}

fn token_is_valid(state: &AppState, request: &Request<Body>) -> bool {
    let Some(expected) = state.api_token() else {
        return true;
    };
    bearer_token(request)
        .or_else(|| header_token(request))
        .is_some_and(|actual| constant_time_eq(actual.as_bytes(), expected.as_bytes()))
}

fn bearer_token(request: &Request<Body>) -> Option<&str> {
    request
        .headers()
        .get(header::AUTHORIZATION)?
        .to_str()
        .ok()?
        .strip_prefix("Bearer ")
}

fn header_token(request: &Request<Body>) -> Option<&str> {
    request.headers().get("x-sfo-api-token")?.to_str().ok()
}

fn constant_time_eq(actual: &[u8], expected: &[u8]) -> bool {
    let mut diff = actual.len() ^ expected.len();
    for (left, right) in actual.iter().zip(expected.iter()) {
        diff |= usize::from(left ^ right);
    }
    diff == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constant_time_eq_requires_same_bytes_and_length() {
        assert!(constant_time_eq(b"abc", b"abc"));
        assert!(!constant_time_eq(b"abc", b"abd"));
        assert!(!constant_time_eq(b"abc", b"abcd"));
    }
}
