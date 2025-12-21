from datetime import datetime, timedelta, time as dt_time
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Block, Task, Project
from ..utils.rules import parse_block_type
from ..utils.coach import build_coach_context_json, block_summary, task_summary, project_summary
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


@router.get("/blocks", response_class=HTMLResponse)
def blocks(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    blocks = (
        db.query(Block)
        .options(selectinload(Block.project))
        .order_by(Block.date.asc(), Block.start_time.asc().nulls_last())
        .all()
    )
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    sched_ready = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(Task.block_type.isnot(None), Task.duration_minutes.isnot(None), Task.scheduled_for.is_(None))
        .order_by(Task.when_bucket.asc(), Task.created_at.desc())
        .all()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="blocks",
        screen_title="Blocks",
        screen_data={
            "blocks": [block_summary(b) for b in blocks],
            "projects": [project_summary(p) for p in projects],
            "ready_to_schedule": [task_summary(t) for t in sched_ready],
        },
        db=db,
    )
    return templates.TemplateResponse(
        "blocks.html",
        {
            "request": request,
            "blocks": blocks,
            "projects": projects,
            "sched_ready": sched_ready,
            "form_success": request.query_params.get("success"),
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/blocks/schedule")
def schedule_task(
    task_id: int = Form(...),
    date: str = Form(...),
    start_time: str = Form(...),
    duration_minutes: int = Form(...),
    block_type: str = Form(...),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        date_val = datetime.strptime(date, "%Y-%m-%d").date()
        start_val = datetime.strptime(start_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time")

    dur = max(5, duration_minutes)
    start_dt = datetime.combine(date_val, start_val)
    end_dt = start_dt + timedelta(minutes=dur)
    if end_dt.date() != date_val:
        raise HTTPException(status_code=400, detail="Blocks cannot span midnight.")
    end_val: dt_time = end_dt.time()
    parsed_block_type = parse_block_type(block_type)
    if parsed_block_type is None:
        raise HTTPException(status_code=400, detail="Block type is required.")

    block = Block(
        title=task.verb_noun,
        date=date_val,
        start_time=start_val,
        end_time=end_val,
        block_type=parsed_block_type,
        project_id=task.project_id,
        task_id=task.id,
        notes=None,
    )
    task.scheduled_for = date_val
    db.add(block)
    db.add(task)
    db.commit()
    return RedirectResponse(url="/blocks?success=Scheduled", status_code=303)


@router.post("/blocks/appointment")
def create_appointment(
    title: str = Form(...),
    date: str = Form(...),
    start_time: str = Form(...),
    duration_minutes: int = Form(...),
    block_type: str = Form(...),
    project_id: str | None = Form(""),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        date_val = datetime.strptime(date, "%Y-%m-%d").date()
        start_val = datetime.strptime(start_time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time")

    parsed_block_type = parse_block_type(block_type)
    if parsed_block_type is None:
        raise HTTPException(status_code=400, detail="Block type is required.")

    dur = max(5, duration_minutes)
    start_dt = datetime.combine(date_val, start_val)
    end_dt = start_dt + timedelta(minutes=dur)
    if end_dt.date() != date_val:
        raise HTTPException(status_code=400, detail="Blocks cannot span midnight.")
    end_val: dt_time = end_dt.time()

    pid = int(project_id) if project_id not in (None, "", "null") else None
    block = Block(
        title=title.strip(),
        date=date_val,
        start_time=start_val,
        end_time=end_val,
        block_type=parsed_block_type,
        project_id=pid,
        task_id=None,
        notes=notes.strip() if notes else None,
    )
    db.add(block)
    db.commit()
    return RedirectResponse(url="/blocks?success=Appointment+added", status_code=303)


@router.post("/blocks/unschedule")
def unschedule_block(
    block_id: int = Form(...),
    db: Session = Depends(get_db),
):
    block = db.get(Block, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    if block.task_id:
        task = db.get(Task, block.task_id)
        if task:
            task.scheduled_for = None
            db.add(task)
    db.delete(block)
    db.commit()
    return RedirectResponse(url="/blocks?success=Unscheduled", status_code=303)


@router.post("/blocks/update")
def update_block(
    block_id: int = Form(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    block = db.get(Block, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    cleaned_title = (title or "").strip()
    block.title = cleaned_title or None
    db.add(block)
    db.commit()
    return RedirectResponse(url="/blocks?success=Updated", status_code=303)
