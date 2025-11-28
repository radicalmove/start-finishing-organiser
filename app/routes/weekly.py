from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, ProjectCategory, Task

router = APIRouter()


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
        .filter(Task.resurface_on.isnot(None), Task.resurface_on <= upcoming)
        .order_by(Task.resurface_on.asc(), Task.created_at.desc())
        .all()
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
        },
    )
