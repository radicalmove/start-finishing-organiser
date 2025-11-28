from datetime import datetime, timedelta, time as dt_time
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Block, Task, BlockType, WhenBucket

router = APIRouter()


@router.get("/blocks", response_class=HTMLResponse)
def blocks(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    blocks = (
        db.query(Block)
        .order_by(Block.date.asc(), Block.start_time.asc().nulls_last())
        .all()
    )
    sched_ready = (
        db.query(Task)
        .filter(Task.block_type.isnot(None), Task.duration_minutes.isnot(None), Task.scheduled_for.is_(None))
        .order_by(Task.when_bucket.asc(), Task.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "blocks.html",
        {
            "request": request,
            "blocks": blocks,
            "sched_ready": sched_ready,
            "form_success": request.query_params.get("success"),
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
    end_val: dt_time = end_dt.time()

    block = Block(
        date=date_val,
        start_time=start_val,
        end_time=end_val,
        block_type=BlockType(block_type),
        project_id=task.project_id,
        task_id=task.id,
        notes=None,
    )
    task.scheduled_for = date_val
    db.add(block)
    db.add(task)
    db.commit()
    return RedirectResponse(url="/blocks?success=Scheduled", status_code=303)


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
