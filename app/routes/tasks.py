from __future__ import annotations

from datetime import datetime, date, timedelta
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import (
    Alignment,
    BlockType,
    Project,
    Task,
    TaskStatus,
    WhenBucket,
)
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json, project_summary, task_summary
from ..utils.rules import parse_block_type, parse_optional_int

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _task_is_active(task: Task) -> bool:
    return task.status in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}

def _build_tasks_context(request: Request, db: Session) -> dict:
    templates = request.app.state.templates
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    rows = (
        db.query(Task)
        .options(selectinload(Task.project))
        .order_by(Task.created_at.desc())
        .all()
    )
    active_tasks = [t for t in rows if _task_is_active(t)]
    completed_tasks = [t for t in rows if t.status == TaskStatus.DONE]
    archived_tasks = [t for t in rows if t.status in {TaskStatus.ARCHIVED, TaskStatus.CANCELLED}]

    buckets = {
        WhenBucket.TODAY: [],
        WhenBucket.WEEK: [],
        WhenBucket.MONTH: [],
        WhenBucket.QUARTER: [],
        WhenBucket.LATER: [],
    }
    for task in active_tasks:
        buckets[task.when_bucket].append(task)

    by_project: dict[int | None, list[Task]] = {}
    for task in active_tasks:
        by_project.setdefault(task.project_id, []).append(task)

    week_start = date.today() - timedelta(days=date.today().weekday())
    completed_this_week = [
        t for t in completed_tasks if t.completed_at and t.completed_at.date() >= week_start
    ]

    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="tasks",
        screen_title="Tasks",
        screen_data={
            "projects": [project_summary(p) for p in projects],
            "tasks": [task_summary(t) for t in active_tasks],
            "completed_count": len(completed_tasks),
        },
        db=db,
    )

    return {
        "templates": templates,
        "projects": projects,
        "rows": rows,
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "archived_tasks": archived_tasks,
        "buckets": buckets,
        "by_project": by_project,
        "completed_this_week": completed_this_week,
        "coach_context_json": coach_context_json,
    }


def _render_tasks_page(request: Request, context: dict, page_mode: str, view_mode: str | None = None):
    templates = context["templates"]
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "projects": context["projects"],
            "buckets": context["buckets"],
            "by_project": context["by_project"],
            "active_tasks": context["active_tasks"],
            "completed_tasks": context["completed_tasks"],
            "completed_this_week": context["completed_this_week"],
            "archived_tasks": context["archived_tasks"],
            "form_success": request.query_params.get("success"),
            "coach_context_json": context["coach_context_json"],
            "alignments": [a.value for a in Alignment],
            "block_types": [b.value for b in BlockType],
            "page_mode": page_mode,
            "view_mode": view_mode,
        },
    )


def _safe_redirect(next_url: str | None, fallback: str, message: str | None = None) -> RedirectResponse:
    url = next_url if next_url and next_url.startswith("/") else fallback
    if message:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}success={quote_plus(message)}"
    return RedirectResponse(url=url, status_code=303)


@router.get("/tasks", response_class=HTMLResponse)
def tasks_board(request: Request):
    return RedirectResponse(url="/tasks/time", status_code=302)


@router.get("/tasks/time", response_class=HTMLResponse)
def tasks_time(request: Request, db: Session = Depends(get_db)):
    context = _build_tasks_context(request, db)
    return _render_tasks_page(request, context, page_mode="active_time", view_mode="time")


@router.get("/tasks/project", response_class=HTMLResponse)
def tasks_project(request: Request, db: Session = Depends(get_db)):
    context = _build_tasks_context(request, db)
    return _render_tasks_page(request, context, page_mode="active_project", view_mode="project")


@router.get("/tasks/completed", response_class=HTMLResponse)
def tasks_completed(request: Request, db: Session = Depends(get_db)):
    context = _build_tasks_context(request, db)
    return _render_tasks_page(request, context, page_mode="completed")


@router.get("/tasks/archived", response_class=HTMLResponse)
def tasks_archived(request: Request, db: Session = Depends(get_db)):
    context = _build_tasks_context(request, db)
    return _render_tasks_page(request, context, page_mode="archived")


@router.post("/tasks/update")
def update_task(
    task_id: int = Form(...),
    verb_noun: str | None = Form(None),
    description: str | None = Form(None),
    project_id: str | None = Form(""),
    when_bucket: WhenBucket = Form(WhenBucket.TODAY),
    block_type: str | None = Form(""),
    duration_minutes: str | None = Form(None),
    frog: bool = Form(False),
    alignment: str | None = Form(None),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if verb_noun is not None:
        cleaned = verb_noun.strip()
        if cleaned:
            task.verb_noun = cleaned
    if description is not None:
        task.description = description.strip() or None

    task.project_id = int(project_id) if project_id not in (None, "", "null") else None
    task.when_bucket = when_bucket
    task.block_type = parse_block_type(block_type) if block_type not in (None, "", "null") else None
    duration_value = parse_optional_int(duration_minutes)
    if duration_value is not None and duration_value <= 0:
        duration_value = None
    task.duration_minutes = duration_value
    task.frog = bool(frog)
    task.alignment = Alignment(alignment) if alignment else None
    task.in_inbox = False

    db.add(task)
    db.commit()
    return _safe_redirect(next_url, "/tasks/time", "Saved")


@router.post("/tasks/complete")
def complete_task(
    task_id: int = Form(...),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.DONE
    task.completed_at = datetime.utcnow()
    task.in_inbox = False
    db.add(task)
    db.commit()
    return _safe_redirect(next_url, "/tasks/time", f"Completed: {task.verb_noun}")


@router.post("/tasks/reopen")
def reopen_task(
    task_id: int = Form(...),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.PENDING
    task.completed_at = None
    db.add(task)
    db.commit()
    return _safe_redirect(next_url, "/tasks/completed", "Reopened")


@router.post("/tasks/archive")
def archive_task(
    task_id: int = Form(...),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.ARCHIVED
    task.in_inbox = False
    task.archived_from_inbox = False
    db.add(task)
    db.commit()
    return _safe_redirect(next_url, "/tasks/archived", "Archived")


@router.post("/tasks/archive/bulk")
def archive_tasks_bulk(
    task_ids: list[int] | None = Form(None),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if not task_ids:
        return _safe_redirect(next_url, "/tasks/completed", "Nothing to archive")
    tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
    for task in tasks:
        task.status = TaskStatus.ARCHIVED
        task.in_inbox = False
        task.archived_from_inbox = False
        db.add(task)
    db.commit()
    return _safe_redirect(next_url, "/tasks/archived", "Archived")


@router.post("/tasks/restore")
def restore_task(
    task_id: int = Form(...),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.PENDING
    task.completed_at = None
    if task.archived_from_inbox:
        task.in_inbox = True
        task.when_bucket = WhenBucket.LATER
        task.archived_from_inbox = False
    else:
        task.in_inbox = False
    db.add(task)
    db.commit()
    return _safe_redirect(next_url, "/tasks/time", "Restored")
