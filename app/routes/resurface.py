from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Task, WhenBucket
from ..utils.coach import build_coach_context_json, task_summary
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


@router.get("/resurface", response_class=HTMLResponse)
def resurface(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    today = date.today()
    upcoming = today + timedelta(days=7)
    due = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(Task.resurface_on.isnot(None), Task.resurface_on <= upcoming)
        .order_by(Task.resurface_on.asc(), Task.created_at.desc())
        .all()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="resurface",
        screen_title="Resurface",
        screen_data={
            "today": today.isoformat(),
            "due_tasks": [task_summary(t) for t in due],
        },
        db=db,
    )
    return templates.TemplateResponse(
        "resurface.html",
        {
            "request": request,
            "due_tasks": due,
            "today": today,
            "form_success": request.query_params.get("success"),
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/resurface/{task_id}")
def pull_into_week(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.when_bucket = WhenBucket.WEEK
    task.resurface_on = None
    db.add(task)
    db.commit()
    return RedirectResponse(url="/resurface?success=Moved to week", status_code=303)
