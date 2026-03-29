from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
from ..services import (
    apply_task_update,
    archive_task as mutate_archive_task,
    complete_task as mutate_complete_task,
    reopen_task as mutate_reopen_task,
    restore_task as mutate_restore_task,
)
from ..utils.coach import build_coach_context_json, project_summary, task_summary
from ..utils.inbox_intents import (
    INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_PARK_LET_GO,
)

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


ACTIVE_TASK_STATUSES = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
ARCHIVED_TASK_STATUSES = (TaskStatus.ARCHIVED, TaskStatus.CANCELLED)
NON_WORK_CONTAINERS = (
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_PARK_LET_GO,
)
TASK_HISTORY_PAGE_SIZE = 40


def _parse_page(raw: str | None) -> int:
    try:
        page = int(raw or "1")
    except ValueError:
        return 1
    return page if page > 0 else 1


def _paginate(total_count: int, requested_page: int, page_size: int = TASK_HISTORY_PAGE_SIZE) -> dict[str, int | bool]:
    if total_count <= 0:
        return {
            "page": 1,
            "page_size": page_size,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
            "prev_page": 1,
            "next_page": 1,
        }

    total_pages = max(1, math.ceil(total_count / page_size))
    page = max(1, min(requested_page, total_pages))
    return {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1 if page > 1 else 1,
        "next_page": page + 1 if page < total_pages else total_pages,
    }


def _build_tasks_context(request: Request, db: Session) -> dict:
    templates = request.app.state.templates
    completed_requested_page = _parse_page(request.query_params.get("completed_page"))
    archived_requested_page = _parse_page(request.query_params.get("archived_page"))
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    active_tasks = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(
            Task.status.in_(ACTIVE_TASK_STATUSES),
            Task.intake_container.notin_(NON_WORK_CONTAINERS),
        )
        .order_by(
            Task.when_bucket.asc(),
            Task.priority.asc().nulls_last(),
            Task.created_at.desc(),
        )
        .all()
    )
    completed_total_count = db.query(Task).filter(Task.status == TaskStatus.DONE).count()
    completed_pagination = _paginate(completed_total_count, completed_requested_page)
    completed_offset = (int(completed_pagination["page"]) - 1) * TASK_HISTORY_PAGE_SIZE
    completed_tasks = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(Task.status == TaskStatus.DONE)
        .order_by(Task.completed_at.desc().nulls_last(), Task.created_at.desc())
        .offset(completed_offset)
        .limit(TASK_HISTORY_PAGE_SIZE)
        .all()
    )
    archived_total_count = (
        db.query(Task)
        .filter(Task.status.in_(ARCHIVED_TASK_STATUSES))
        .count()
    )
    archived_pagination = _paginate(archived_total_count, archived_requested_page)
    archived_offset = (int(archived_pagination["page"]) - 1) * TASK_HISTORY_PAGE_SIZE
    archived_tasks = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(Task.status.in_(ARCHIVED_TASK_STATUSES))
        .order_by(Task.created_at.desc())
        .offset(archived_offset)
        .limit(TASK_HISTORY_PAGE_SIZE)
        .all()
    )

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
    week_start_dt = datetime.combine(week_start, time.min)
    completed_this_week = (
        db.query(Task)
        .filter(
            Task.status == TaskStatus.DONE,
            Task.completed_at.isnot(None),
            Task.completed_at >= week_start_dt,
        )
        .order_by(Task.completed_at.desc())
        .all()
    )

    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="tasks",
        screen_title="Tasks",
        screen_data={
            "projects": [project_summary(p) for p in projects],
            "tasks": [task_summary(t) for t in active_tasks],
            "completed_count": completed_total_count,
        },
        db=db,
    )

    return {
        "templates": templates,
        "projects": projects,
        "active_tasks": active_tasks,
        "completed_tasks": completed_tasks,
        "completed_total_count": completed_total_count,
        "completed_pagination": completed_pagination,
        "archived_tasks": archived_tasks,
        "archived_total_count": archived_total_count,
        "archived_pagination": archived_pagination,
        "buckets": buckets,
        "by_project": by_project,
        "completed_this_week": completed_this_week,
        "coach_context_json": coach_context_json,
    }


def _render_tasks_page(request: Request, context: dict, page_mode: str, view_mode: str | None = None):
    templates = context["templates"]
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "request": request,
            "projects": context["projects"],
            "buckets": context["buckets"],
            "by_project": context["by_project"],
            "active_tasks": context["active_tasks"],
            "completed_tasks": context["completed_tasks"],
            "completed_total_count": context["completed_total_count"],
            "completed_pagination": context["completed_pagination"],
            "completed_this_week": context["completed_this_week"],
            "archived_tasks": context["archived_tasks"],
            "archived_total_count": context["archived_total_count"],
            "archived_pagination": context["archived_pagination"],
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
    request: Request,
    task_id: int = Form(...),
    verb_noun: str | None = Form(None),
    description: str | None = Form(None),
    project_id: str | None = Form(""),
    when_bucket: WhenBucket = Form(WhenBucket.TODAY),
    block_type: str | None = Form(""),
    duration_minutes: str | None = Form(None),
    frog: bool = Form(False),
    alignment: str | None = Form(None),
    send_to_inbox: bool = Form(False),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    apply_task_update(
        task,
        verb_noun=verb_noun,
        description=description,
        project_id=project_id,
        when_bucket=when_bucket,
        block_type=block_type,
        duration_minutes=duration_minutes,
        frog=frog,
        alignment=alignment,
        send_to_inbox=send_to_inbox,
    )

    db.add(task)
    db.commit()
    accept_header = request.headers.get("accept", "")
    wants_json = request.headers.get("x-requested-with") == "fetch" or "application/json" in accept_header
    if wants_json:
        return JSONResponse(
            {
                "status": "ok",
                "task_id": task.id,
                "when_bucket": task.when_bucket.value,
                "project_id": task.project_id,
                "in_inbox": task.in_inbox,
            }
        )
    message = "Sent to Inbox" if send_to_inbox else "Saved"
    return _safe_redirect(next_url, "/tasks/time", message)


@router.post("/tasks/complete")
def complete_task(
    task_id: int = Form(...),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    mutate_complete_task(task)
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
    mutate_reopen_task(task)
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
    mutate_archive_task(task)
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
        mutate_archive_task(task)
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
    mutate_restore_task(task)
    db.add(task)
    db.commit()
    return _safe_redirect(next_url, "/tasks/time", "Restored")
