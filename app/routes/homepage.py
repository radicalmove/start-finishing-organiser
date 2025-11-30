from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import quote_plus
from datetime import date, datetime

from ..db import get_db
from ..models import (
    Project,
    ProjectStatus,
    ProjectCategory,
    Task,
    WhenBucket,
    Block,
    BlockType,
)
from ..utils.rules import enforce_weekly_cap, compose_why_text

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def landing(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates

    today = date.today()
    now = datetime.now().time()
    projects = (
        db.query(Project)
        .filter(Project.status != ProjectStatus.ARCHIVED)
        .order_by(Project.active_this_week.desc(), Project.created_at.desc())
        .all()
    )
    today_tasks = (
        db.query(Task)
        .filter(Task.when_bucket == WhenBucket.TODAY)
        .order_by(Task.block_type.asc().nulls_last(), Task.priority.asc().nulls_last())
        .all()
    )
    inbox_tasks = (
        db.query(Task)
        .filter(Task.when_bucket.in_([WhenBucket.LATER, WhenBucket.MONTH, WhenBucket.QUARTER]))
        .order_by(Task.created_at.desc())
        .all()
    )
    week_blocks = (
        db.query(Block)
        .order_by(Block.date.asc(), Block.start_time.asc().nulls_last())
        .all()
    )

    # Soft enforcement snapshot for the 4 work + 3 personal rule
    weekly_work = [p for p in projects if p.active_this_week and p.category == ProjectCategory.WORK]
    weekly_personal = [
        p for p in projects if p.active_this_week and p.category == ProjectCategory.PERSONAL
    ]
    sched_ready = (
        db.query(Task)
        .filter(Task.block_type.isnot(None), Task.duration_minutes.isnot(None), Task.scheduled_for.is_(None))
        .order_by(Task.when_bucket.asc(), Task.created_at.desc())
        .all()
    )
    todays_blocks = [b for b in week_blocks if b.date == today]
    # Determine current block based on time if start/end present
    current_block = None
    upcoming_blocks = []
    timeline_events = []
    now_action = None
    calendar_events = []
    day_start_minutes = 6 * 60
    day_total_minutes = 16 * 60  # 6am-10pm
    for b in todays_blocks:
        if b.start_time and b.end_time and b.start_time <= now <= b.end_time:
            current_block = b
            if b.project:
                now_action = f"{b.block_type.value.title()} block • {b.project.title}"
            else:
                now_action = f"{b.block_type.value.title()} block"
        elif b.start_time and b.start_time > now:
            upcoming_blocks.append(b)
        timeline_events.append(
            {
                "label": f"{b.block_type.value.title()}",
                "start": b.start_time,
                "end": b.end_time,
                "project": b.project.title if b.project else None,
            }
        )
        if b.start_time:
            start_min = b.start_time.hour * 60 + b.start_time.minute
            end_min = (
                b.end_time.hour * 60 + b.end_time.minute
                if b.end_time
                else start_min + 30
            )
            top_pct = max(0, (start_min - day_start_minutes) / day_total_minutes * 100)
            height_pct = max(5, (end_min - start_min) / day_total_minutes * 100)
            calendar_events.append(
                {
                    "label": b.block_type.value.title(),
                    "project": b.project.title if b.project else None,
                    "top": top_pct,
                    "height": height_pct,
                    "start_display": b.start_time.strftime("%-I:%M %p"),
                    "end_display": b.end_time.strftime("%-I:%M %p") if b.end_time else "",
                    "type": b.block_type.value,
                }
            )
    upcoming_blocks = sorted(upcoming_blocks, key=lambda x: (x.start_time or datetime.max.time()))

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "projects": projects,
            "today_tasks": today_tasks,
            "inbox_tasks": inbox_tasks,
            "week_blocks": week_blocks,
            "todays_blocks": todays_blocks,
            "current_block": current_block,
            "upcoming_blocks": upcoming_blocks,
            "timeline_events": sorted(timeline_events, key=lambda e: e["start"] or datetime.max.time()),
            "calendar_events": calendar_events,
            "now_action": now_action,
            "weekly_work_count": len(weekly_work),
            "weekly_personal_count": len(weekly_personal),
            "form_error": request.query_params.get("error"),
            "form_success": request.query_params.get("success"),
            "sched_ready": sched_ready,
        },
    )


@router.post("/projects/form")
def create_project(
    title: str = Form(...),
    category: ProjectCategory = Form(ProjectCategory.WORK),
    time_horizon: str = Form("week"),
    include_this_week: str = Form("yes"),
    description: str | None = Form(None),
    why_link_text: str | None = Form(None),
    why_tags: list[str] | None = Form(None),
    db: Session = Depends(get_db),
):
    active_this_week = include_this_week.lower() == "yes" or time_horizon == "week"
    if active_this_week:
        try:
            enforce_weekly_cap(db, category, True)
        except HTTPException as exc:
            msg = quote_plus(str(exc.detail))
            return RedirectResponse(url=f"/?error={msg}", status_code=303)

    project = Project(
        title=title.strip(),
        category=category,
        description=description or None,
        active_this_week=active_this_week,
        why_link_text=compose_why_text(why_link_text, why_tags),
        time_horizon=time_horizon,
    )
    db.add(project)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/tasks/form")
def create_task(
    verb_noun: str = Form(...),
    project_id: str | None = Form(""),
    description: str | None = Form(None),
    when_bucket: WhenBucket = Form(WhenBucket.TODAY),
    block_type: str | None = Form(""),
    duration_minutes: int | None = Form(None),
    frog: bool = Form(False),
    db: Session = Depends(get_db),
):
    pid = int(project_id) if project_id not in (None, "", "null") else None
    btype = block_type if block_type not in (None, "", "null") else None

    task = Task(
        verb_noun=verb_noun.strip(),
        project_id=pid,
        description=description or None,
        when_bucket=when_bucket,
        block_type=BlockType(btype) if btype else None,
        duration_minutes=duration_minutes or None,
        frog=frog,
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url="/?success=Saved", status_code=303)
