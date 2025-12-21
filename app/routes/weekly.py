from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Project, ProjectCategory, Task
from ..utils.coach import build_coach_context_json, project_summary, task_summary
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
        .filter(Task.resurface_on.isnot(None), Task.resurface_on <= upcoming)
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
