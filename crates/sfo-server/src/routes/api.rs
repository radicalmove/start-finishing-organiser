use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, patch, post};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use sfo_core::{
    BackupManifest, Block, BlockCreate, BlockId, BlockUpdate, ImportDryRunReport,
    ImportDryRunRequest, Page, Project, ProjectCreate, ProjectId, ProjectUpdate,
    PythonSqliteImportReport, PythonSqliteImportRequest, QuickCapture, Task, TaskCreate, TaskId,
    TaskUpdate,
};
use sfo_services::{PlanningService, ScheduleService, ServiceError, SystemService};
use std::str::FromStr;

use crate::AppState;

#[derive(Debug, Deserialize)]
struct PageQuery {
    page: Option<i64>,
    page_size: Option<i64>,
}

#[derive(Debug, Serialize)]
struct ErrorBody {
    detail: String,
}

#[derive(Debug)]
struct ApiError {
    status: StatusCode,
    detail: String,
}

impl ApiError {
    fn bad_request(detail: impl Into<String>) -> Self {
        Self {
            status: StatusCode::BAD_REQUEST,
            detail: detail.into(),
        }
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (
            self.status,
            Json(ErrorBody {
                detail: self.detail,
            }),
        )
            .into_response()
    }
}

impl From<ServiceError> for ApiError {
    fn from(error: ServiceError) -> Self {
        match error {
            ServiceError::NotFound { entity } => Self {
                status: StatusCode::NOT_FOUND,
                detail: format!("{entity} not found"),
            },
            ServiceError::WeeklyCap {
                category,
                current,
                cap,
            } => Self {
                status: StatusCode::BAD_REQUEST,
                detail: format!(
                    "Weekly cap reached for {} projects ({current}/{cap}). Drop or pause one to add another.",
                    category.as_str()
                ),
            },
            ServiceError::Validation { field, message } => Self {
                status: StatusCode::BAD_REQUEST,
                detail: format!("invalid {field}: {message}"),
            },
            ServiceError::Db(error) => Self {
                status: StatusCode::INTERNAL_SERVER_ERROR,
                detail: error.to_string(),
            },
        }
    }
}

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/projects", get(list_projects).post(create_project))
        .route(
            "/projects/{project_id}",
            patch(update_project).delete(delete_project),
        )
        .route("/tasks", get(list_tasks).post(create_task))
        .route("/tasks/{task_id}", patch(update_task).delete(delete_task))
        .route("/tasks/{task_id}/complete", post(complete_task))
        .route("/tasks/{task_id}/reopen", post(reopen_task))
        .route("/tasks/{task_id}/archive", post(archive_task))
        .route("/tasks/{task_id}/restore", post(restore_task))
        .route("/blocks", get(list_blocks).post(create_block))
        .route(
            "/blocks/{block_id}",
            patch(update_block).delete(delete_block),
        )
        .route("/inbox/quick-capture", post(quick_capture))
        .route(
            "/import/python-sqlite/dry-run",
            post(dry_run_python_sqlite_import),
        )
        .route("/import/python-sqlite", post(import_python_sqlite))
        .route("/export/backup", post(export_backup))
}

async fn list_projects(
    State(state): State<AppState>,
    Query(query): Query<PageQuery>,
) -> Result<Json<Page<Project>>, ApiError> {
    let service = PlanningService::new(state.db);
    let page = service
        .list_projects(query.page.unwrap_or(1), query.page_size.unwrap_or(50))
        .await?;
    Ok(Json(page))
}

async fn create_project(
    State(state): State<AppState>,
    Json(payload): Json<ProjectCreate>,
) -> Result<(StatusCode, Json<Project>), ApiError> {
    let service = PlanningService::new(state.db);
    let project = service.create_project(payload).await?;
    Ok((StatusCode::CREATED, Json(project)))
}

async fn update_project(
    State(state): State<AppState>,
    Path(project_id): Path<String>,
    Json(payload): Json<ProjectUpdate>,
) -> Result<Json<Project>, ApiError> {
    let service = PlanningService::new(state.db);
    let project = service
        .update_project(parse_project_id(&project_id)?, payload)
        .await?;
    Ok(Json(project))
}

async fn delete_project(
    State(state): State<AppState>,
    Path(project_id): Path<String>,
) -> Result<StatusCode, ApiError> {
    let service = PlanningService::new(state.db);
    service
        .delete_project(parse_project_id(&project_id)?)
        .await?;
    Ok(StatusCode::NO_CONTENT)
}

async fn list_tasks(
    State(state): State<AppState>,
    Query(query): Query<PageQuery>,
) -> Result<Json<Page<Task>>, ApiError> {
    let service = PlanningService::new(state.db);
    let page = service
        .list_tasks(query.page.unwrap_or(1), query.page_size.unwrap_or(50))
        .await?;
    Ok(Json(page))
}

async fn create_task(
    State(state): State<AppState>,
    Json(payload): Json<TaskCreate>,
) -> Result<(StatusCode, Json<Task>), ApiError> {
    let service = PlanningService::new(state.db);
    let task = service.create_task(payload).await?;
    Ok((StatusCode::CREATED, Json(task)))
}

async fn update_task(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
    Json(payload): Json<TaskUpdate>,
) -> Result<Json<Task>, ApiError> {
    let service = PlanningService::new(state.db);
    let task = service
        .update_task(parse_task_id(&task_id)?, payload)
        .await?;
    Ok(Json(task))
}

async fn delete_task(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
) -> Result<StatusCode, ApiError> {
    let service = PlanningService::new(state.db);
    service.delete_task(parse_task_id(&task_id)?).await?;
    Ok(StatusCode::NO_CONTENT)
}

async fn complete_task(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
) -> Result<Json<Task>, ApiError> {
    let service = PlanningService::new(state.db);
    Ok(Json(service.complete_task(parse_task_id(&task_id)?).await?))
}

async fn reopen_task(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
) -> Result<Json<Task>, ApiError> {
    let service = PlanningService::new(state.db);
    Ok(Json(service.reopen_task(parse_task_id(&task_id)?).await?))
}

async fn archive_task(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
) -> Result<Json<Task>, ApiError> {
    let service = PlanningService::new(state.db);
    Ok(Json(service.archive_task(parse_task_id(&task_id)?).await?))
}

async fn restore_task(
    State(state): State<AppState>,
    Path(task_id): Path<String>,
) -> Result<Json<Task>, ApiError> {
    let service = PlanningService::new(state.db);
    Ok(Json(service.restore_task(parse_task_id(&task_id)?).await?))
}

async fn quick_capture(
    State(state): State<AppState>,
    Json(payload): Json<QuickCapture>,
) -> Result<(StatusCode, Json<Task>), ApiError> {
    let service = PlanningService::new(state.db);
    let task = service.quick_capture(payload).await?;
    Ok((StatusCode::CREATED, Json(task)))
}

async fn list_blocks(
    State(state): State<AppState>,
    Query(query): Query<PageQuery>,
) -> Result<Json<Page<Block>>, ApiError> {
    let service = ScheduleService::new(state.db);
    let page = service
        .list_blocks(query.page.unwrap_or(1), query.page_size.unwrap_or(50))
        .await?;
    Ok(Json(page))
}

async fn create_block(
    State(state): State<AppState>,
    Json(payload): Json<BlockCreate>,
) -> Result<(StatusCode, Json<Block>), ApiError> {
    let service = ScheduleService::new(state.db);
    let block = service.create_block(payload).await?;
    Ok((StatusCode::CREATED, Json(block)))
}

async fn update_block(
    State(state): State<AppState>,
    Path(block_id): Path<String>,
    Json(payload): Json<BlockUpdate>,
) -> Result<Json<Block>, ApiError> {
    let service = ScheduleService::new(state.db);
    let block = service
        .update_block(parse_block_id(&block_id)?, payload)
        .await?;
    Ok(Json(block))
}

async fn delete_block(
    State(state): State<AppState>,
    Path(block_id): Path<String>,
) -> Result<StatusCode, ApiError> {
    let service = ScheduleService::new(state.db);
    service.delete_block(parse_block_id(&block_id)?).await?;
    Ok(StatusCode::NO_CONTENT)
}

async fn dry_run_python_sqlite_import(
    State(state): State<AppState>,
    Json(payload): Json<ImportDryRunRequest>,
) -> Result<Json<ImportDryRunReport>, ApiError> {
    let service = SystemService::new(state.db);
    let report = service
        .dry_run_python_sqlite_import(payload.source_path)
        .await?;
    Ok(Json(report))
}

async fn import_python_sqlite(
    State(state): State<AppState>,
    Json(payload): Json<PythonSqliteImportRequest>,
) -> Result<Json<PythonSqliteImportReport>, ApiError> {
    let service = SystemService::new(state.db);
    let backup_dir = payload.backup_dir.map(std::path::PathBuf::from);
    let report = service
        .import_python_sqlite(payload.source_path, backup_dir)
        .await?;
    Ok(Json(report))
}

async fn export_backup(State(state): State<AppState>) -> Result<Json<BackupManifest>, ApiError> {
    let service = SystemService::new(state.db);
    Ok(Json(service.backup_manifest().await?))
}

fn parse_project_id(value: &str) -> Result<ProjectId, ApiError> {
    ProjectId::from_str(value).map_err(|_| ApiError::bad_request("invalid project id"))
}

fn parse_task_id(value: &str) -> Result<TaskId, ApiError> {
    TaskId::from_str(value).map_err(|_| ApiError::bad_request("invalid task id"))
}

fn parse_block_id(value: &str) -> Result<BlockId, ApiError> {
    BlockId::from_str(value).map_err(|_| ApiError::bad_request("invalid block id"))
}
