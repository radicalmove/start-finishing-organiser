import os
import ssl
from datetime import date, datetime, time, timedelta
from urllib.parse import quote_plus
from urllib.request import Request as UrlRequest, urlopen
import certifi

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload
from icalendar import Calendar

from ..db import get_db
from ..models import (
    Project,
    ProjectStatus,
    ProjectCategory,
    Task,
    WhenBucket,
    Block,
)
from ..utils.rules import enforce_weekly_cap, compose_why_text, parse_block_type
from ..utils.coach import build_coach_context_json, block_summary, task_summary
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])
# in-memory cache of the parsed Cozi ICS feed
_COZI_CACHE = {"fetched_at": None, "events": [], "status": "", "url": None}
_COZI_CACHE_TTL_SECONDS = 60
CALENDAR_START_HOUR = 6
CALENDAR_END_HOUR = 23
CALENDAR_HOURS = CALENDAR_END_HOUR - CALENDAR_START_HOUR
CALENDAR_HOUR_HEIGHT_PX = 48


def _split_cozi_label(label: str) -> tuple[str | None, str | None]:
    if ":" not in label:
        return None, None
    prefix, remainder = label.split(":", 1)
    prefix = prefix.strip()
    remainder = remainder.strip()
    if not prefix:
        return None, None
    return f"{prefix}:", remainder or None


def _fetch_cozi_calendar() -> tuple[list[dict], str]:
    """Fetch and cache Cozi ICS events (normalized) with a short TTL."""
    url = os.getenv("COZI_ICS_URL")
    if not url:
        return [], "COZI_ICS_URL not set"

    now = datetime.now().astimezone()  # cache timestamp in local tz
    if (
        _COZI_CACHE.get("url") == url
        and _COZI_CACHE.get("fetched_at")
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
        return _COZI_CACHE.get("events", []), status

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
            # iCal all-day events use an exclusive end date; subtract a tick for display logic.
            end_dt = datetime.combine(end, time.min) - timedelta(seconds=1)
        else:
            end_dt = end

        if isinstance(start_dt, datetime) and start_dt.tzinfo:
            start_dt = start_dt.astimezone().replace(tzinfo=None)
        if isinstance(end_dt, datetime) and end_dt and end_dt.tzinfo:
            end_dt = end_dt.astimezone().replace(tzinfo=None)

        if end_dt is None:
            end_dt = start_dt + timedelta(hours=1)

        label_prefix, label_suffix = _split_cozi_label(summary)
        events.append(
            {
                "label": summary,
                "label_prefix": label_prefix,
                "label_suffix": label_suffix,
                "start": start_dt,
                "end": end_dt,
            }
        )

    _COZI_CACHE["fetched_at"] = now
    _COZI_CACHE["events"] = events
    _COZI_CACHE["status"] = f"OK ({len(events)} events)"
    _COZI_CACHE["url"] = url
    return events, _COZI_CACHE["status"]


def _cozi_events_touching_day(events: list[dict], target_date: date) -> list[dict]:
    return [ev for ev in events if ev["start"].date() <= target_date <= ev["end"].date()]


def _fetch_cozi_events(target_date: date) -> tuple[list[dict], str]:
    events, status = _fetch_cozi_calendar()
    return _cozi_events_touching_day(events, target_date), status


def _build_week_calendar(
    *,
    week_start: date,
    day_start_minutes: float,
    day_total_minutes: float,
    blocks: list[Block],
    cozi_events: list[dict],
    today: date,
) -> list[dict]:
    week_end = week_start + timedelta(days=6)
    week_days = [week_start + timedelta(days=offset) for offset in range(7)]

    blocks_by_day: dict[date, list[Block]] = {d: [] for d in week_days}
    for b in blocks:
        if b.date in blocks_by_day:
            blocks_by_day[b.date].append(b)

    cozi_by_day: dict[date, list[dict]] = {d: [] for d in week_days}
    for ev in cozi_events:
        ev_start = ev["start"].date()
        ev_end = ev["end"].date()
        if ev_end < week_start or ev_start > week_end:
            continue
        cur = max(ev_start, week_start)
        last = min(ev_end, week_end)
        while cur <= last:
            cozi_by_day[cur].append(ev)
            cur += timedelta(days=1)

    week_calendar = []
    window_start = day_start_minutes
    window_end = day_start_minutes + day_total_minutes
    for d in week_days:
        day_events = []
        for b in sorted(blocks_by_day[d], key=lambda block: block.start_time or time.max):
            if not b.start_time:
                continue
            label = b.title or b.block_type.value.title()
            start_min = b.start_time.hour * 60 + b.start_time.minute
            end_min = (
                b.end_time.hour * 60 + b.end_time.minute if b.end_time else start_min + 30
            )
            top_pct = max(0, (start_min - day_start_minutes) / day_total_minutes * 100)
            height_pct = max(5, (end_min - start_min) / day_total_minutes * 100)
            day_events.append(
                {
                    "label": label,
                    "title": b.title,
                    "block_id": b.id,
                    "project": b.project.title if b.project else None,
                    "top": top_pct,
                    "height": height_pct,
                    "start_display": b.start_time.strftime("%-I:%M %p"),
                    "end_display": b.end_time.strftime("%-I:%M %p") if b.end_time else "",
                    "type": b.block_type.value,
                }
            )

        for ev in cozi_by_day[d]:
            start_dt = ev["start"]
            end_dt = ev["end"]
            start_min = start_dt.hour * 60 + start_dt.minute
            end_min = end_dt.hour * 60 + end_dt.minute
            start_display = start_dt.strftime("%-I:%M %p")
            end_display = end_dt.strftime("%-I:%M %p")
            if d > start_dt.date():
                start_min = 0
                start_display = "12:00 AM"
            if d < end_dt.date():
                end_min = 24 * 60
                end_display = "11:59 PM"
            effective_start = max(window_start, start_min)
            effective_end = min(window_end, end_min)
            if effective_end <= window_start or effective_start >= window_end:
                continue
            top_pct = max(0, (effective_start - window_start) / day_total_minutes * 100)
            height_pct = max(5, (effective_end - effective_start) / day_total_minutes * 100)
            name_prefix = (ev["label"] or "").lower()
            extra_class = None
            if name_prefix.startswith("brynlee"):
                extra_class = "cozi-brynlee"
            elif name_prefix.startswith("jessica"):
                extra_class = "cozi-jessica"
            day_events.append(
                {
                    "label": ev["label"],
                    "label_prefix": ev.get("label_prefix"),
                    "label_suffix": ev.get("label_suffix"),
                    "project": None,
                    "top": top_pct,
                    "height": height_pct,
                    "start_display": start_display,
                    "end_display": end_display,
                    "type": "external",
                    "extra_class": extra_class,
                }
            )

        week_calendar.append(
            {
                "date": d,
                "iso": d.isoformat(),
                "weekday": d.strftime("%a"),
                "label": f"{d.strftime('%b')} {d.day}",
                "is_today": d == today,
                "events": sorted(day_events, key=lambda item: item.get("top", 0)),
            }
        )

    return week_calendar


def _calendar_event_context(events: list[dict]) -> list[dict]:
    context = []
    for ev in events:
        context.append(
            {
                "label": ev.get("label"),
                "start": ev.get("start_display"),
                "end": ev.get("end_display"),
                "type": ev.get("type"),
                "project": ev.get("project"),
                "block_id": ev.get("block_id"),
            }
        )
    return context


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
        .options(selectinload(Task.project))
        .filter(Task.when_bucket == WhenBucket.TODAY)
        .order_by(Task.block_type.asc().nulls_last(), Task.priority.asc().nulls_last())
        .all()
    )
    inbox_tasks = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(Task.when_bucket.in_([WhenBucket.LATER, WhenBucket.MONTH, WhenBucket.QUARTER]))
        .order_by(Task.created_at.desc())
        .all()
    )
    week_blocks = (
        db.query(Block)
        .options(selectinload(Block.project))
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
        .options(selectinload(Task.project))
        .filter(Task.block_type.isnot(None), Task.duration_minutes.isnot(None), Task.scheduled_for.is_(None))
        .order_by(Task.when_bucket.asc(), Task.created_at.desc())
        .all()
    )
    todays_blocks = [b for b in week_blocks if b.date == today]
    cozi_all_events, cozi_status = _fetch_cozi_calendar()
    cozi_events_today = _cozi_events_touching_day(cozi_all_events, today)
    cozi_last_updated = None
    if _COZI_CACHE.get("fetched_at"):
        local_dt = _COZI_CACHE["fetched_at"].astimezone()
        cozi_last_updated = local_dt.strftime("%d %b %I:%M %p")
    cozi_error = None if cozi_status.startswith("OK") else cozi_status
    # Determine current block based on time if start/end present
    current_block = None
    upcoming_blocks = []
    timeline_events = []
    now_action = None
    calendar_events = []
    # Timeline window used for percentage positioning (hour rows are 48px tall in CSS)
    day_start_minutes = CALENDAR_START_HOUR * 60
    day_total_minutes = CALENDAR_HOURS * 60
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
            label = b.title or f"{b.block_type.value.title()} block"
            if b.project:
                now_action = f"{label} • {b.project.title}"
            else:
                now_action = label
        elif b.start_time and b.start_time > now:
            upcoming_blocks.append(b)
        label = b.title or b.block_type.value.title()
        timeline_events.append(
            {
                "label": label,
                "start": b.start_time,
                "end": b.end_time,
                "project": b.project.title if b.project else None,
            }
        )
        if b.start_time:
            label = b.title or b.block_type.value.title()
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
                    "label": label,
                    "title": b.title,
                    "block_id": b.id,
                    "project": b.project.title if b.project else None,
                    "top": top_pct,
                    "height": height_pct,
                    "start_display": b.start_time.strftime("%-I:%M %p"),
                    "end_display": b.end_time.strftime("%-I:%M %p") if b.end_time else "",
                    "type": b.block_type.value,
                }
            )

    for ev in cozi_events_today:
        start_dt = ev["start"]
        end_dt = ev["end"]
        start_min = start_dt.hour * 60 + start_dt.minute
        end_min = end_dt.hour * 60 + end_dt.minute
        start_display = start_dt.strftime("%-I:%M %p")
        end_display = end_dt.strftime("%-I:%M %p")
        if today > start_dt.date():
            start_min = 0
            start_display = "12:00 AM"
        if today < end_dt.date():
            end_min = 24 * 60
            end_display = "11:59 PM"
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
                "label_prefix": ev.get("label_prefix"),
                "label_suffix": ev.get("label_suffix"),
                "project": None,
                "top": top_pct,
                "height": height_pct,
                "start_display": start_display,
                "end_display": end_display,
                "type": "external",
                "extra_class": extra_class,
            }
        )
    upcoming_blocks = sorted(upcoming_blocks, key=lambda x: (x.start_time or datetime.max.time()))
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="home",
        screen_title="Home",
        screen_data={
            "today": today.isoformat(),
            "now_action": now_action,
            "today_tasks": [task_summary(t) for t in today_tasks],
            "inbox_tasks": [task_summary(t) for t in inbox_tasks],
            "current_block": block_summary(current_block) if current_block else None,
            "upcoming_blocks": [block_summary(b) for b in upcoming_blocks],
            "calendar_events": _calendar_event_context(calendar_events),
            "cozi_status": cozi_status,
            "cozi_event_count": len(cozi_events_today),
            "cozi_error": cozi_error,
        },
        db=db,
    )

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
            "cozi_event_count": len(cozi_events_today),
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
            "cozi_error": cozi_error,
            "calendar_start_hour": CALENDAR_START_HOUR,
            "calendar_end_hour": CALENDAR_END_HOUR,
            "calendar_hours": CALENDAR_HOURS,
            "calendar_hour_height": CALENDAR_HOUR_HEIGHT_PX,
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/calendar/week", response_class=HTMLResponse)
def week_calendar_screen(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates

    today = date.today()
    week_start = today
    week_end = week_start + timedelta(days=6)

    week_blocks = (
        db.query(Block)
        .options(selectinload(Block.project))
        .filter(Block.date >= week_start, Block.date <= week_end)
        .order_by(Block.date.asc(), Block.start_time.asc().nulls_last())
        .all()
    )

    cozi_all_events, cozi_status = _fetch_cozi_calendar()
    cozi_last_updated = None
    if _COZI_CACHE.get("fetched_at"):
        local_dt = _COZI_CACHE["fetched_at"].astimezone()
        cozi_last_updated = local_dt.strftime("%d %b %I:%M %p")
    cozi_error = None if cozi_status.startswith("OK") else cozi_status
    cozi_week_event_count = len(
        [
            ev
            for ev in cozi_all_events
            if ev["end"].date() >= week_start and ev["start"].date() <= week_end
        ]
    )

    day_start_minutes = CALENDAR_START_HOUR * 60
    day_total_minutes = CALENDAR_HOURS * 60
    week_calendar = _build_week_calendar(
        week_start=week_start,
        day_start_minutes=day_start_minutes,
        day_total_minutes=day_total_minutes,
        blocks=week_blocks,
        cozi_events=cozi_all_events,
        today=today,
    )
    week_context = []
    for day in week_calendar:
        events = []
        for ev in day.get("events", []):
            events.append(
                {
                    "label": ev.get("label"),
                    "start": ev.get("start_display"),
                    "end": ev.get("end_display"),
                    "type": ev.get("type"),
                    "project": ev.get("project"),
                }
            )
        week_context.append(
            {
                "date": day.get("iso"),
                "weekday": day.get("weekday"),
                "label": day.get("label"),
                "is_today": day.get("is_today"),
                "events": events,
            }
        )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="week_calendar",
        screen_title="Week calendar",
        screen_data={
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "calendar": week_context,
            "cozi_status": cozi_status,
            "cozi_event_count": cozi_week_event_count,
            "cozi_error": cozi_error,
        },
        db=db,
    )

    return templates.TemplateResponse(
        "week_calendar.html",
        {
            "request": request,
            "week_calendar": week_calendar,
            "cozi_week_event_count": cozi_week_event_count,
            "cozi_last_updated": cozi_last_updated,
            "cozi_error": cozi_error,
            "calendar_start_hour": CALENDAR_START_HOUR,
            "calendar_end_hour": CALENDAR_END_HOUR,
            "calendar_hours": CALENDAR_HOURS,
            "calendar_hour_height": CALENDAR_HOUR_HEIGHT_PX,
            "coach_context_json": coach_context_json,
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
        block_type=parse_block_type(btype),
        duration_minutes=duration_minutes or None,
        frog=frog,
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url="/?success=Saved", status_code=303)
