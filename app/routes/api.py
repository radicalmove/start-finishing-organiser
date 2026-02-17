import math
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Alignment,
    Block,
    BlockType,
    Project,
    ProjectCategory,
    ProjectSize,
    ProjectStatus,
    SuccessLevel,
    Task,
    TaskStatus,
    WhenBucket,
)
from ..security import require_api_auth

router = APIRouter(dependencies=[Depends(require_api_auth)])


# ---------- Schemas ----------
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: ProjectCategory = ProjectCategory.WORK
    size: Optional[ProjectSize] = None
    time_horizon: Optional[str] = None
    target_date: Optional[date] = None
    level_of_success: Optional[SuccessLevel] = None
    why_link_text: Optional[str] = None
    active_this_week: bool = False


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    category: Optional[ProjectCategory] = None
    size: Optional[ProjectSize] = None
    time_horizon: Optional[str] = None
    target_date: Optional[date] = None
    level_of_success: Optional[SuccessLevel] = None
    why_link_text: Optional[str] = None
    active_this_week: Optional[bool] = None


class TaskCreate(BaseModel):
    verb_noun: str
    project_id: Optional[int] = None
    description: Optional[str] = None
    in_inbox: bool = False
    when_bucket: WhenBucket = WhenBucket.LATER
    block_type: Optional[BlockType] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    frog: bool = False
    alignment: Optional[Alignment] = None
    first_action: Optional[str] = None
    scheduled_for: Optional[date] = None


class TaskUpdate(BaseModel):
    verb_noun: Optional[str] = None
    description: Optional[str] = None
    in_inbox: Optional[bool] = None
    when_bucket: Optional[WhenBucket] = None
    block_type: Optional[BlockType] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    frog: Optional[bool] = None
    alignment: Optional[Alignment] = None
    first_action: Optional[str] = None
    scheduled_for: Optional[date] = None
    status: Optional[TaskStatus] = None


class ProjectOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: ProjectCategory
    status: ProjectStatus
    size: Optional[ProjectSize] = None
    time_horizon: Optional[str] = None
    target_date: Optional[date] = None
    level_of_success: Optional[SuccessLevel] = None
    why_link_text: Optional[str] = None
    active_this_week: bool
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class TaskOut(BaseModel):
    id: int
    project_id: Optional[int] = None
    verb_noun: str
    description: Optional[str] = None
    in_inbox: bool
    when_bucket: WhenBucket
    block_type: Optional[BlockType] = None
    priority: Optional[int] = None
    frog: bool
    alignment: Optional[Alignment] = None
    first_action: Optional[str] = None
    scheduled_for: Optional[date] = None
    status: TaskStatus
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: list[ProjectOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class TaskListResponse(BaseModel):
    items: list[TaskOut]
    page: int
    page_size: int
    total: int
    total_pages: int


# ---------- Helpers ----------
def _enforce_weekly_cap(db: Session, category: ProjectCategory, make_active: bool) -> None:
    if not make_active:
        return
    cap = 4 if category == ProjectCategory.WORK else 3
    current = (
        db.query(Project)
        .filter(Project.category == category, Project.active_this_week.is_(True))
        .count()
    )
    if current >= cap:
        raise HTTPException(
            status_code=400,
            detail=f"Weekly cap reached for {category.value} projects "
            f"({current}/{cap}). Drop or pause one to add another.",
        )


def _pagination_meta(total: int, requested_page: int, page_size: int) -> tuple[int, int]:
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    page = max(1, min(requested_page, total_pages))
    return page, total_pages


# ---------- Project endpoints ----------
@router.get("/projects", response_model=ProjectListResponse)
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total = db.query(Project).count()
    resolved_page, total_pages = _pagination_meta(total, page, page_size)
    rows = (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .offset((resolved_page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": rows,
        "page": resolved_page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.post("/projects", status_code=201, response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    _enforce_weekly_cap(db, payload.category, payload.active_this_week)
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.active_this_week is True:
        _enforce_weekly_cap(db, payload.category or project.category, True)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return None


# ---------- Task endpoints ----------
@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    total = db.query(Task).count()
    resolved_page, total_pages = _pagination_meta(total, page, page_size)
    rows = (
        db.query(Task)
        .order_by(Task.when_bucket.asc(), Task.priority.asc().nulls_last(), Task.created_at.desc())
        .offset((resolved_page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": rows,
        "page": resolved_page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.post("/tasks", status_code=201, response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return None
