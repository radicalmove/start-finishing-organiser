from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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

router = APIRouter()


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
    when_bucket: Optional[WhenBucket] = None
    block_type: Optional[BlockType] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    frog: Optional[bool] = None
    alignment: Optional[Alignment] = None
    first_action: Optional[str] = None
    scheduled_for: Optional[date] = None
    status: Optional[TaskStatus] = None


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


# ---------- Project endpoints ----------
@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).order_by(Project.created_at.desc()).all()
    return rows


@router.post("/projects", status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    _enforce_weekly_cap(db, payload.category, payload.active_this_week)
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/projects/{project_id}")
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
@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    rows = (
        db.query(Task)
        .order_by(Task.when_bucket.asc(), Task.priority.asc().nulls_last(), Task.created_at.desc())
        .all()
    )
    return rows


@router.post("/tasks", status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/tasks/{task_id}")
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
