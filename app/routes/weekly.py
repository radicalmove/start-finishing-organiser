from datetime import date, timedelta
import json
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Project, ProjectCategory, Task, TaskStatus, GuidanceEvent
from ..utils.coach import build_coach_context_json, project_summary, task_summary
from ..utils.rules import enforce_weekly_cap
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


@router.get("/weekly", response_class=HTMLResponse)
def weekly_review(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    projects = (
        db.query(Project)
        .filter(Project.status != "archived")
        .order_by(Project.active_this_week.desc(), Project.created_at.desc())
        .all()
    )
    weekly_work = [p for p in projects if p.active_this_week and p.category == ProjectCategory.WORK]
    weekly_personal = [
        p for p in projects if p.active_this_week and p.category == ProjectCategory.PERSONAL
    ]

    today = date.today()
    upcoming = today + timedelta(days=7)
    due_resurface = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(
            Task.resurface_on.isnot(None),
            Task.resurface_on <= upcoming,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED, TaskStatus.CANCELLED]),
        )
        .order_by(Task.resurface_on.asc(), Task.created_at.desc())
        .all()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="weekly_review",
        screen_title="Weekly review",
        screen_data={
            "projects": [project_summary(p) for p in projects],
            "weekly_work_count": len(weekly_work),
            "weekly_personal_count": len(weekly_personal),
            "due_resurface": [task_summary(t) for t in due_resurface],
        },
        db=db,
    )

    return templates.TemplateResponse(
        "weekly_review.html",
        {
            "request": request,
            "projects": projects,
            "weekly_work_count": len(weekly_work),
            "weekly_personal_count": len(weekly_personal),
            "due_resurface": due_resurface,
            "form_success": request.query_params.get("success"),
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/weekly/wizard", response_class=HTMLResponse)
def weekly_wizard(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    projects = (
        db.query(Project)
        .filter(Project.status != "archived")
        .order_by(Project.active_this_week.desc(), Project.created_at.desc())
        .all()
    )
    weekly_work = [p for p in projects if p.active_this_week and p.category == ProjectCategory.WORK]
    weekly_personal = [
        p for p in projects if p.active_this_week and p.category == ProjectCategory.PERSONAL
    ]
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    upcoming = today + timedelta(days=7)
    due_resurface = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(
            Task.resurface_on.isnot(None),
            Task.resurface_on <= upcoming,
            Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED, TaskStatus.CANCELLED]),
        )
        .order_by(Task.resurface_on.asc(), Task.created_at.desc())
        .all()
    )
    completed_this_week = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(
            Task.status == TaskStatus.DONE,
            Task.completed_at.isnot(None),
            Task.completed_at >= week_start,
        )
        .order_by(Task.completed_at.desc())
        .all()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="weekly_wizard",
        screen_title="Weekly review wizard",
        screen_data={
            "projects": [project_summary(p) for p in projects],
            "weekly_work_count": len(weekly_work),
            "weekly_personal_count": len(weekly_personal),
            "due_resurface": [task_summary(t) for t in due_resurface],
            "completed_tasks": [task_summary(t) for t in completed_this_week],
        },
        db=db,
    )
    return templates.TemplateResponse(
        "weekly_wizard.html",
        {
            "request": request,
            "projects": projects,
            "weekly_work_count": len(weekly_work),
            "weekly_personal_count": len(weekly_personal),
            "due_resurface": due_resurface,
            "completed_this_week": completed_this_week,
            "week_start": week_start,
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/weekly/projects/{project_id}/toggle")
def toggle_weekly_project(
    project_id: int,
    make_active: str = Form("no"),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    should_activate = make_active.lower() in {"1", "true", "yes", "on"}
    if should_activate and not project.active_this_week:
        enforce_weekly_cap(db, project.category, True)
    project.active_this_week = should_activate
    db.add(project)
    db.commit()
    return RedirectResponse(url="/weekly/wizard", status_code=303)


@router.post("/weekly/complete")
def complete_weekly_review(
    wins: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    context = {
        "wins": wins.strip() if wins else None,
        "notes": notes.strip() if notes else None,
    }
    context_json = json.dumps(context, ensure_ascii=True)
    event = GuidanceEvent(code="weekly_review_done", context_json=context_json)
    db.add(event)
    db.commit()
    return RedirectResponse(url="/weekly?success=Weekly review complete", status_code=303)
