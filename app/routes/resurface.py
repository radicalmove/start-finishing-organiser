from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Task, WhenBucket

router = APIRouter()


@router.get("/resurface", response_class=HTMLResponse)
def resurface(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    today = date.today()
    upcoming = today + timedelta(days=7)
    due = (
        db.query(Task)
        .filter(Task.resurface_on.isnot(None), Task.resurface_on <= upcoming)
        .order_by(Task.resurface_on.asc(), Task.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "resurface.html",
        {
            "request": request,
            "due_tasks": due,
            "today": today,
            "form_success": request.query_params.get("success"),
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
