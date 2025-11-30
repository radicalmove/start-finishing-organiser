import os
import ssl
from datetime import date, datetime, time, timedelta
from urllib.parse import quote_plus
from urllib.request import Request as UrlRequest, urlopen
import certifi

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from icalendar import Calendar

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
_COZI_CACHE = {"fetched_at": None, "date": None, "events": [], "status": ""}  # in-memory cache of ICS feed
_COZI_CACHE_TTL_SECONDS = 60


def _fetch_cozi_events(target_date: date) -> tuple[list[dict], str]:
    """
    Fetch and cache Cozi ICS events for a given date.
    Returns (events, status message). Uses a short TTL to avoid hammering Cozi.
    """
    url = os.getenv("COZI_ICS_URL")
    if not url:
        return [], "COZI_ICS_URL not set"

    now = datetime.now().astimezone()  # cache timestamp in local tz
    if (
        _COZI_CACHE["date"] == target_date
        and _COZI_CACHE["fetched_at"]
        and (now - _COZI_CACHE["fetched_at"]).total_seconds() < _COZI_CACHE_TTL_SECONDS
    ):
        return _COZI_CACHE["events"], _COZI_CACHE.get("status", "")

    events: list[dict] = []
    try:
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        req = UrlRequest(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (StartFinishing/0.2)",
                "Accept": "text/calendar,*/*",
            },
        )
        with urlopen(req, timeout=10, context=ssl_ctx) as resp:
            data = resp.read()
        cal = Calendar.from_ical(data)
    except Exception as exc:
        status = f"Cozi fetch failed: {exc}"
        return (
            (_COZI_CACHE["events"] if _COZI_CACHE["date"] == target_date else []),
            status,
        )

    for component in cal.walk("VEVENT"):
        dtstart = component.get("dtstart")
        if not dtstart:
            continue
        dtend = component.get("dtend")
        summary = (component.get("summary") or "").strip() or "Cozi event"

        start = dtstart.dt
        end = dtend.dt if dtend else None

        if isinstance(start, date) and not isinstance(start, datetime):
            start_dt = datetime.combine(start, time.min)
        else:
            start_dt = start

        if isinstance(end, date) and not isinstance(end, datetime):
            end_dt = datetime.combine(end, time.min)
        else:
            end_dt = end

        if isinstance(start_dt, datetime) and start_dt.tzinfo:
            start_dt = start_dt.astimezone().replace(tzinfo=None)
        if isinstance(end_dt, datetime) and end_dt and end_dt.tzinfo:
            end_dt = end_dt.astimezone().replace(tzinfo=None)

        if end_dt is None:
            end_dt = start_dt + timedelta(hours=1)

        # Keep events that touch the target day
        if not (start_dt.date() <= target_date <= end_dt.date()):
            continue

        events.append({"label": summary, "start": start_dt, "end": end_dt})

    _COZI_CACHE["fetched_at"] = now
    _COZI_CACHE["date"] = target_date
    _COZI_CACHE["events"] = events
    _COZI_CACHE["status"] = f"OK ({len(events)} events)"
    return events, _COZI_CACHE["status"]


@router.get("/", response_class=HTMLResponse)
def landing(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates

    today = date.today()
    now = datetime.now().time()
    now_minutes = datetime.now().hour * 60 + datetime.now().minute
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
    cozi_events, cozi_status = _fetch_cozi_events(today)
    cozi_last_updated = None
    if _COZI_CACHE.get("fetched_at"):
        local_dt = _COZI_CACHE["fetched_at"].astimezone()
        cozi_last_updated = local_dt.strftime("%d %b %I:%M %p")
    # Determine current block based on time if start/end present
    current_block = None
    upcoming_blocks = []
    timeline_events = []
    now_action = None
    calendar_events = []
    # Timeline window used for percentage positioning (hour rows are 48px tall in CSS)
    day_start_minutes = 6.15 * 60
    # 18-hour span here is a visual tweak to better match rendered grid spacing
    day_total_minutes = 16.2 * 60
    now_position = None
    now_label = None
    if day_start_minutes <= now_minutes <= day_start_minutes + day_total_minutes:
        now_position = max(
            0, min(100, (now_minutes - day_start_minutes) / day_total_minutes * 100)
        )
        now_label = datetime.now().strftime("%-I:%M %p")
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

    for ev in cozi_events:
        start_dt = ev["start"]
        end_dt = ev["end"]
        start_min = start_dt.hour * 60 + start_dt.minute
        end_min = end_dt.hour * 60 + end_dt.minute
        window_start = day_start_minutes
        window_end = day_start_minutes + day_total_minutes
        effective_start = max(window_start, start_min)
        effective_end = min(window_end, end_min)
        if effective_end <= window_start or effective_start >= window_end:
            continue
        top_pct = max(0, (effective_start - window_start) / day_total_minutes * 100)
        height_pct = max(5, (effective_end - effective_start) / day_total_minutes * 100)
        # Color-code Cozi events by label prefix if desired (e.g., Brynlee/Jessica)
        name_prefix = (ev["label"] or "").lower()
        extra_class = None
        if name_prefix.startswith("brynlee"):
            extra_class = "cozi-brynlee"
        elif name_prefix.startswith("jessica"):
            extra_class = "cozi-jessica"

        calendar_events.append(
            {
                "label": ev["label"],
                "project": None,
                "top": top_pct,
                "height": height_pct,
                "start_display": start_dt.strftime("%-I:%M %p"),
                "end_display": end_dt.strftime("%-I:%M %p"),
                "type": "external",
                "extra_class": extra_class,
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
            "cozi_event_count": len(cozi_events),
            "cozi_status": cozi_status,
            "cozi_last_updated": cozi_last_updated,
            "server_today": today,
            "now_position": now_position,
            "now_label": now_label,
            "day_start_minutes": day_start_minutes,
            "day_total_minutes": day_total_minutes,
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
