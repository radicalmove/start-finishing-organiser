import os
import ssl
from datetime import date, datetime, time, timedelta
from urllib.parse import quote_plus
from urllib.request import Request as UrlRequest, urlopen
import certifi

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from icalendar import Calendar

from ..db import get_db
from ..models import (
    Project,
    ProjectStatus,
    ProjectCategory,
    Task,
    TaskStatus,
    WhenBucket,
    Block,
    RitualEntry,
    RitualType,
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_UNPROCESSED,
    INBOX_INTENT_PARK_LET_GO,
)
from ..services import (
    apply_task_update,
    archive_inbox_task as mutate_archive_inbox_task,
    restore_inbox_item as mutate_restore_inbox_item,
)
from ..utils.rules import enforce_weekly_cap, compose_why_text
from ..utils.coach import build_coach_context_json, block_summary, task_summary
from ..utils.inbox_intents import (
    INBOX_INTENT_LABELS,
    QUICK_ROUTE_INTENTS,
    apply_inbox_container,
    normalize_inbox_intent,
)
from ..utils.profile import get_profile
from ..utils.projects import project_title_looks_action
from ..utils.time import utc_now, utc_now_naive
from ..security import csrf_protect, require_html_auth, is_safe_redirect

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])
# in-memory cache of the parsed Cozi ICS feed
_COZI_CACHE = {
    "fetched_at": None,
    "events": [],
    "status": "",
    "url": None,
    "next_retry_at": None,
}
_COZI_CACHE_TTL_SECONDS = 60
CALENDAR_START_HOUR = 6
CALENDAR_END_HOUR = 23
CALENDAR_HOURS = CALENDAR_END_HOUR - CALENDAR_START_HOUR
CALENDAR_HOUR_HEIGHT_PX = 48
ACTIVE_TASK_STATUSES = (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
CONTAINER_ROUTE_INTENTS = (
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_PARK_LET_GO,
)
DEFAULT_RECYCLE_BIN_RETENTION_DAYS = 60


def _cozi_timeout_seconds() -> float:
    raw = (os.getenv("SFO_COZI_HTTP_TIMEOUT_SECONDS") or "3.5").strip()
    try:
        value = float(raw)
    except ValueError:
        return 3.5
    return max(0.8, min(value, 20.0))


def _cozi_retry_backoff_seconds() -> int:
    raw = (os.getenv("SFO_COZI_RETRY_BACKOFF_SECONDS") or "90").strip()
    try:
        value = int(raw)
    except ValueError:
        return 90
    return max(10, min(value, 600))


def _wants_json(request: Request) -> bool:
    accept_header = request.headers.get("accept", "")
    return request.headers.get("x-requested-with") == "fetch" or "application/json" in accept_header


def _active_inbox_count(db: Session) -> int:
    return (
        db.query(Task)
        .filter(
            Task.in_inbox.is_(True),
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .count()
    )


def _container_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for intent in CONTAINER_ROUTE_INTENTS:
        counts[intent] = (
            db.query(Task)
            .filter(
                Task.intake_container == intent,
                Task.status.in_(ACTIVE_TASK_STATUSES),
            )
            .count()
        )
    counts["recycle_bin"] = (
        db.query(Task)
        .filter(Task.archived_from_inbox.is_(True), Task.status == TaskStatus.ARCHIVED)
        .count()
    )
    return counts


def _safe_redirect(next_url: str | None, fallback: str, message: str | None = None) -> RedirectResponse:
    url = next_url if is_safe_redirect(next_url) else fallback
    if message:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}success={quote_plus(message)}"
    return RedirectResponse(url=url, status_code=303)


def _recycle_bin_retention_days() -> int:
    raw = (os.getenv("SFO_RECYCLE_BIN_RETENTION_DAYS") or str(DEFAULT_RECYCLE_BIN_RETENTION_DAYS)).strip().lower()
    if raw in {"off", "none", "false", "no", "0"}:
        return 0
    try:
        days = int(raw)
    except ValueError:
        return DEFAULT_RECYCLE_BIN_RETENTION_DAYS
    return max(days, 0)


def _expired_recycle_items_count(db: Session, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = utc_now_naive() - timedelta(days=retention_days)
    return int(
        (
            db.query(Task)
            .filter(
                Task.archived_from_inbox.is_(True),
                Task.status == TaskStatus.ARCHIVED,
                func.coalesce(Task.completed_at, Task.created_at) <= cutoff,
            )
            .count()
        )
        or 0
    )


def _purge_recycle_items_older_than(db: Session, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = utc_now_naive() - timedelta(days=retention_days)
    deleted = (
        db.query(Task)
        .filter(
            Task.archived_from_inbox.is_(True),
            Task.status == TaskStatus.ARCHIVED,
            func.coalesce(Task.completed_at, Task.created_at) <= cutoff,
        )
        .delete(synchronize_session=False)
    ) or 0
    if deleted:
        db.commit()
    return int(deleted)


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
    next_retry_at = _COZI_CACHE.get("next_retry_at")
    if (
        _COZI_CACHE.get("url") == url
        and next_retry_at
        and now < next_retry_at
    ):
        return _COZI_CACHE.get("events", []), _COZI_CACHE.get("status", "Cozi fetch paused")

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
        with urlopen(req, timeout=_cozi_timeout_seconds(), context=ssl_ctx) as resp:
            data = resp.read()
        cal = Calendar.from_ical(data)
    except Exception as exc:
        status = f"Cozi fetch failed: {exc}"
        _COZI_CACHE["url"] = url
        _COZI_CACHE["status"] = status
        _COZI_CACHE["next_retry_at"] = now + timedelta(seconds=_cozi_retry_backoff_seconds())
        return _COZI_CACHE.get("events", []), status

    for component in cal.walk("VEVENT"):
        dtstart = component.get("dtstart")
        if not dtstart:
            continue
        dtend = component.get("dtend")
        summary = (component.get("summary") or "").strip() or "Cozi event"

        start = dtstart.dt
        end = dtend.dt if dtend else None
        is_all_day = isinstance(start, date) and not isinstance(start, datetime)
        if isinstance(end, date) and not isinstance(end, datetime):
            is_all_day = True

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
                "is_all_day": is_all_day,
            }
        )

    _COZI_CACHE["fetched_at"] = now
    _COZI_CACHE["events"] = events
    _COZI_CACHE["status"] = f"OK ({len(events)} events)"
    _COZI_CACHE["url"] = url
    _COZI_CACHE["next_retry_at"] = None
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
            is_all_day = bool(ev.get("is_all_day"))
            if is_all_day:
                start_min = window_start
                end_min = min(window_start + 60, window_end)
                start_display = "All Day event"
                end_display = ""
            else:
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
            extra_class = "event-block--all-day" if is_all_day else None
            if name_prefix.startswith("brynlee"):
                extra_class = f"{extra_class} cozi-brynlee" if extra_class else "cozi-brynlee"
            elif name_prefix.startswith("jessica"):
                extra_class = f"{extra_class} cozi-jessica" if extra_class else "cozi-jessica"
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


def _ritual_context_for_today(db: Session, today: date, now: time) -> dict:
    ritual_entries = (
        db.query(RitualEntry)
        .filter(RitualEntry.entry_date == today)
        .order_by(RitualEntry.created_at.desc())
        .all()
    )
    ritual_by_type: dict[str, RitualEntry] = {}
    for entry in ritual_entries:
        key = entry.ritual_type.value if isinstance(entry.ritual_type, RitualType) else str(entry.ritual_type)
        if key not in ritual_by_type:
            ritual_by_type[key] = entry

    ritual_status = {
        "morning": "morning" in ritual_by_type,
        "midday": "midday" in ritual_by_type,
        "evening": "evening" in ritual_by_type,
    }
    ritual_labels = {
        "morning": "Morning check-in",
        "midday": "Midday reset",
        "evening": "Evening check-out",
    }
    hour = now.hour
    if hour < 11:
        time_bucket = "morning"
    elif hour < 16:
        time_bucket = "midday"
    else:
        time_bucket = "evening"

    ritual_next_key = None
    if not ritual_status.get(time_bucket):
        ritual_next_key = time_bucket
    else:
        order = ["morning", "midday", "evening"]
        start_index = order.index(time_bucket)
        for key in order[start_index + 1 :]:
            if not ritual_status.get(key):
                ritual_next_key = key
                break

    morning_entry = ritual_by_type.get("morning")
    return {
        "ritual_status": ritual_status,
        "ritual_labels": ritual_labels,
        "ritual_next_key": ritual_next_key,
        "ritual_next_label": ritual_labels.get(ritual_next_key) if ritual_next_key else None,
        "today_one_thing": morning_entry.one_thing if morning_entry else None,
        "today_frog": morning_entry.frog if morning_entry else None,
    }


def _home_calendar_state(
    *,
    today: date,
    now: time,
    now_minutes: int,
    todays_blocks: list[Block],
    cozi_events_today: list[dict],
    day_start_minutes: int,
    day_total_minutes: int,
    today_one_thing: str | None,
    today_frog: str | None,
) -> dict:
    current_block = None
    upcoming_blocks: list[Block] = []
    timeline_events: list[dict] = []
    calendar_events: list[dict] = []
    now_action = None
    now_position = None
    now_label = None

    if day_start_minutes <= now_minutes <= day_start_minutes + day_total_minutes:
        now_position = max(
            0, min(100, (now_minutes - day_start_minutes) / day_total_minutes * 100)
        )
        now_label = datetime.now().strftime("%-I:%M %p")

    for block in todays_blocks:
        if block.start_time and block.end_time and block.start_time <= now <= block.end_time:
            current_block = block
            label = block.title or f"{block.block_type.value.title()} block"
            now_action = f"{label} • {block.project.title}" if block.project else label
        elif block.start_time and block.start_time > now:
            upcoming_blocks.append(block)

        timeline_label = block.title or block.block_type.value.title()
        timeline_events.append(
            {
                "label": timeline_label,
                "start": block.start_time,
                "end": block.end_time,
                "project": block.project.title if block.project else None,
            }
        )

        if not block.start_time:
            continue

        start_min = block.start_time.hour * 60 + block.start_time.minute
        end_min = (
            block.end_time.hour * 60 + block.end_time.minute
            if block.end_time
            else start_min + 30
        )
        top_pct = max(0, (start_min - day_start_minutes) / day_total_minutes * 100)
        height_pct = max(5, (end_min - start_min) / day_total_minutes * 100)
        calendar_events.append(
            {
                "label": timeline_label,
                "title": block.title,
                "block_id": block.id,
                "project": block.project.title if block.project else None,
                "top": top_pct,
                "height": height_pct,
                "start_display": block.start_time.strftime("%-I:%M %p"),
                "end_display": block.end_time.strftime("%-I:%M %p") if block.end_time else "",
                "type": block.block_type.value,
            }
        )

    if not now_action:
        if today_one_thing:
            now_action = today_one_thing
        elif today_frog:
            now_action = f"Frog: {today_frog}"

    for ev in cozi_events_today:
        start_dt = ev["start"]
        end_dt = ev["end"]
        is_all_day = bool(ev.get("is_all_day"))
        if is_all_day:
            start_min = day_start_minutes
            end_min = min(day_start_minutes + 60, day_start_minutes + day_total_minutes)
            start_display = "All Day event"
            end_display = ""
        else:
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
        name_prefix = (ev["label"] or "").lower()
        extra_class = "event-block--all-day" if is_all_day else None
        if name_prefix.startswith("brynlee"):
            extra_class = f"{extra_class} cozi-brynlee" if extra_class else "cozi-brynlee"
        elif name_prefix.startswith("jessica"):
            extra_class = f"{extra_class} cozi-jessica" if extra_class else "cozi-jessica"

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
    return {
        "current_block": current_block,
        "upcoming_blocks": upcoming_blocks,
        "timeline_events": timeline_events,
        "calendar_events": calendar_events,
        "now_position": now_position,
        "now_label": now_label,
        "now_action": now_action,
    }


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
        .filter(
            Task.when_bucket == WhenBucket.TODAY,
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(Task.block_type.asc().nulls_last(), Task.priority.asc().nulls_last())
        .all()
    )
    inbox_tasks = (
        db.query(Task)
        .options(selectinload(Task.project))
        .filter(
            Task.in_inbox.is_(True),
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(Task.created_at.desc())
        .all()
    )
    container_counts = _container_counts(db)
    todays_blocks = (
        db.query(Block)
        .options(selectinload(Block.project))
        .filter(Block.date == today)
        .order_by(Block.start_time.asc().nulls_last())
        .all()
    )

    # Soft enforcement snapshot for the 4 work + 3 personal rule
    weekly_work = [p for p in projects if p.active_this_week and p.category == ProjectCategory.WORK]
    weekly_personal = [
        p for p in projects if p.active_this_week and p.category == ProjectCategory.PERSONAL
    ]
    ritual_context = _ritual_context_for_today(db, today, now)
    ritual_status = ritual_context["ritual_status"]
    ritual_labels = ritual_context["ritual_labels"]
    ritual_next_key = ritual_context["ritual_next_key"]
    ritual_next_label = ritual_context["ritual_next_label"]
    today_one_thing = ritual_context["today_one_thing"]
    today_frog = ritual_context["today_frog"]

    profile = get_profile(db)
    profile_why = profile.why_primary if profile else None
    profile_missing = profile is None or not profile.why_primary

    cozi_all_events, cozi_status = _fetch_cozi_calendar()
    cozi_events_today = _cozi_events_touching_day(cozi_all_events, today)
    cozi_last_updated = None
    if _COZI_CACHE.get("fetched_at"):
        local_dt = _COZI_CACHE["fetched_at"].astimezone()
        cozi_last_updated = local_dt.strftime("%d %b %I:%M %p")
    cozi_error = None if cozi_status.startswith("OK") else cozi_status

    # Timeline window used for percentage positioning (hour rows are 48px tall in CSS).
    day_start_minutes = CALENDAR_START_HOUR * 60
    day_total_minutes = CALENDAR_HOURS * 60
    home_calendar = _home_calendar_state(
        today=today,
        now=now,
        now_minutes=now_minutes,
        todays_blocks=todays_blocks,
        cozi_events_today=cozi_events_today,
        day_start_minutes=day_start_minutes,
        day_total_minutes=day_total_minutes,
        today_one_thing=today_one_thing,
        today_frog=today_frog,
    )
    current_block = home_calendar["current_block"]
    upcoming_blocks = home_calendar["upcoming_blocks"]
    timeline_events = home_calendar["timeline_events"]
    calendar_events = home_calendar["calendar_events"]
    now_position = home_calendar["now_position"]
    now_label = home_calendar["now_label"]
    now_action = home_calendar["now_action"]
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
            "why_primary": profile_why,
            "one_thing": today_one_thing,
            "frog": today_frog,
        },
        db=db,
    )

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "request": request,
            "projects": projects,
            "today_tasks": today_tasks,
            "inbox_tasks": inbox_tasks,
            "container_counts": container_counts,
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
            "cozi_error": cozi_error,
            "calendar_start_hour": CALENDAR_START_HOUR,
            "calendar_end_hour": CALENDAR_END_HOUR,
            "calendar_hours": CALENDAR_HOURS,
            "calendar_hour_height": CALENDAR_HOUR_HEIGHT_PX,
            "ritual_status": ritual_status,
            "ritual_next_key": ritual_next_key,
            "ritual_next_label": ritual_next_label,
            "ritual_labels": ritual_labels,
            "profile_why": profile_why,
            "today_one_thing": today_one_thing,
            "today_frog": today_frog,
            "profile_missing": profile_missing,
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
        request,
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
    target_date: str = Form(...),
    verb_check_ack: str | None = Form(None),
    description: str | None = Form(None),
    why_link_text: str | None = Form(None),
    why_tags: list[str] | None = Form(None),
    db: Session = Depends(get_db),
):
    cleaned_title = title.strip()
    if not cleaned_title:
        return RedirectResponse(url="/?error=Title+is+required", status_code=303)

    if not project_title_looks_action(cleaned_title):
        if (verb_check_ack or "").strip().lower() not in {"1", "true", "yes", "on"}:
            msg = quote_plus(
                "Project title should start with an action verb (e.g. Move Sam to Atlanta)."
            )
            return RedirectResponse(url=f"/?error={msg}", status_code=303)

    try:
        parsed_target_date = datetime.strptime(target_date.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        msg = quote_plus("Set a target date for this project. No date = no finish.")
        return RedirectResponse(url=f"/?error={msg}", status_code=303)

    active_this_week = include_this_week.lower() == "yes" or time_horizon == "week"
    if active_this_week:
        try:
            enforce_weekly_cap(db, category, True)
        except HTTPException as exc:
            msg = quote_plus(str(exc.detail))
            return RedirectResponse(url=f"/?error={msg}", status_code=303)

    project = Project(
        title=cleaned_title,
        category=category,
        description=description or None,
        active_this_week=active_this_week,
        why_link_text=compose_why_text(why_link_text, why_tags),
        time_horizon=time_horizon,
        target_date=parsed_target_date,
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
    duration_minutes: str | None = Form(None),
    frog: bool = Form(False),
    db: Session = Depends(get_db),
):
    task = Task(
        verb_noun=verb_noun.strip(),
        in_inbox=False,
        when_bucket=when_bucket,
    )
    apply_task_update(
        task,
        verb_noun=verb_noun,
        description=description,
        project_id=project_id,
        when_bucket=when_bucket,
        block_type=block_type,
        duration_minutes=duration_minutes,
        frog=frog,
    )
    db.add(task)
    db.commit()
    return RedirectResponse(url="/?success=Saved", status_code=303)


@router.post("/inbox/update")
def update_inbox_item(
    request: Request,
    task_id: int = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task or not task.in_inbox:
        if _wants_json(request):
            return JSONResponse(
                {"ok": False, "message": "Inbox item not found"},
                status_code=404,
            )
        return RedirectResponse(url="/?error=Inbox+item+not+found", status_code=303)
    apply_task_update(task, description=description)
    db.add(task)
    db.commit()
    if _wants_json(request):
        return JSONResponse(
            {
                "ok": True,
                "message": "Saved",
                "task_id": task.id,
                "description": task.description or "",
            }
        )
    return RedirectResponse(url="/?success=Saved", status_code=303)


@router.post("/inbox/archive")
def archive_inbox_item(
    request: Request,
    task_id: int = Form(...),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task or not task.in_inbox:
        if _wants_json(request):
            return JSONResponse(
                {"ok": False, "message": "Inbox item not found"},
                status_code=404,
            )
        return RedirectResponse(url="/?error=Inbox+item+not+found", status_code=303)
    mutate_archive_inbox_task(task)
    db.add(task)
    db.commit()
    if _wants_json(request):
        return JSONResponse(
            {
                "ok": True,
                "message": "Moved to Recycle Bin",
                "task_id": task.id,
                "inbox_count": _active_inbox_count(db),
                "removed": True,
            }
        )
    return RedirectResponse(url="/?success=Moved+to+Recycle+Bin", status_code=303)


@router.post("/inbox/route")
def route_inbox_item(
    request: Request,
    task_id: int = Form(...),
    intent: str = Form(...),
    db: Session = Depends(get_db),
):
    normalized_intent = normalize_inbox_intent(intent)
    if normalized_intent not in QUICK_ROUTE_INTENTS:
        if _wants_json(request):
            return JSONResponse(
                {"ok": False, "message": "Invalid inbox intent"},
                status_code=400,
            )
        return RedirectResponse(url="/?error=Invalid+inbox+intent", status_code=303)

    task = db.get(Task, task_id)
    if not task or not task.in_inbox:
        if _wants_json(request):
            return JSONResponse(
                {"ok": False, "message": "Inbox item not found"},
                status_code=404,
            )
        return RedirectResponse(url="/?error=Inbox+item+not+found", status_code=303)

    apply_inbox_container(task, normalized_intent)
    db.add(task)
    db.commit()
    message = f"Saved to {INBOX_INTENT_LABELS.get(normalized_intent, 'container')}"
    if normalized_intent == INBOX_INTENT_PARK_LET_GO:
        message = "Parked for later review"

    if _wants_json(request):
        return JSONResponse(
            {
                "ok": True,
                "message": message,
                "task_id": task.id,
                "intent": normalized_intent,
                "view_url": "/inbox/containers",
                "inbox_count": _active_inbox_count(db),
                "removed": True,
                "undo_available": True,
            }
        )
    return RedirectResponse(url=f"/?success={quote_plus(message)}", status_code=303)


@router.post("/inbox/undo")
def undo_inbox_route(
    request: Request,
    task_id: int = Form(...),
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    task = db.get(Task, task_id)
    if not task:
        if _wants_json(request):
            return JSONResponse(
                {"ok": False, "message": "Inbox item not found"},
                status_code=404,
            )
        return RedirectResponse(url="/?error=Inbox+item+not+found", status_code=303)

    if task.in_inbox:
        if _wants_json(request):
            return JSONResponse(
                {
                    "ok": True,
                    "message": "Already in Inbox",
                    "task_id": task.id,
                    "inbox_count": _active_inbox_count(db),
                }
            )
        return _safe_redirect(next_url, "/", "Already in Inbox")

    if task.intake_container not in QUICK_ROUTE_INTENTS:
        if _wants_json(request):
            return JSONResponse(
                {"ok": False, "message": "Nothing to undo for this item"},
                status_code=400,
            )
        target = next_url if is_safe_redirect(next_url) else "/"
        sep = "&" if "?" in target else "?"
        return RedirectResponse(url=f"{target}{sep}error=Nothing+to+undo+for+this+item", status_code=303)

    mutate_restore_inbox_item(task)
    db.add(task)
    db.commit()
    if _wants_json(request):
        return JSONResponse(
            {
                "ok": True,
                "message": "Returned to Inbox",
                "task_id": task.id,
                "inbox_count": _active_inbox_count(db),
                "restored": True,
            }
        )
    return _safe_redirect(next_url, "/", "Returned to Inbox")


@router.post("/inbox/recycle/empty")
def empty_recycle_bin(
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    deleted = (
        db.query(Task)
        .filter(
            Task.archived_from_inbox.is_(True),
            Task.status == TaskStatus.ARCHIVED,
        )
        .delete(synchronize_session=False)
    ) or 0
    if deleted:
        db.commit()
        message = f"Recycle bin emptied ({deleted})"
    else:
        message = "Recycle bin already empty"
    return _safe_redirect(next_url, "/inbox/containers?tab=recycle", message)


@router.post("/inbox/recycle/purge-expired")
def purge_expired_recycle_items(
    next_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    retention_days = _recycle_bin_retention_days()
    if retention_days <= 0:
        return _safe_redirect(next_url, "/inbox/containers?tab=recycle", "Auto-cleanup is off")
    deleted = _purge_recycle_items_older_than(db, retention_days)
    if deleted:
        message = (
            f"Removed {deleted} expired recycle item"
            if deleted == 1
            else f"Removed {deleted} expired recycle items"
        )
    else:
        message = "No expired recycle items"
    return _safe_redirect(next_url, "/inbox/containers?tab=recycle", message)


@router.get("/inbox/containers", response_class=HTMLResponse)
def inbox_containers(
    request: Request,
    tab: str | None = None,
    db: Session = Depends(get_db),
):
    templates = request.app.state.templates
    active_tab = (tab or "learning").strip().lower()
    if active_tab not in {"learning", "enjoy", "parked", "recycle"}:
        active_tab = "learning"
    recycle_retention_days = _recycle_bin_retention_days()
    recycle_expired_count = _expired_recycle_items_count(db, recycle_retention_days)

    learning_items = (
        db.query(Task)
        .filter(
            Task.intake_container == INBOX_INTENT_LEARN_EXPLORE,
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(Task.created_at.desc())
        .all()
    )
    enjoy_items = (
        db.query(Task)
        .filter(
            Task.intake_container == INBOX_INTENT_ENJOY_RECOVER,
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(Task.created_at.desc())
        .all()
    )
    parked_items = (
        db.query(Task)
        .filter(
            Task.intake_container == INBOX_INTENT_PARK_LET_GO,
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .order_by(Task.created_at.desc())
        .all()
    )
    recycle_items = (
        db.query(Task)
        .filter(
            Task.archived_from_inbox.is_(True),
            Task.status == TaskStatus.ARCHIVED,
        )
        .order_by(Task.created_at.desc())
        .all()
    )
    now_naive = utc_now_naive()
    recycle_oldest_days: int | None = None
    for item in recycle_items:
        archived_at = item.completed_at or item.created_at
        if not archived_at:
            continue
        archived_naive = archived_at.replace(tzinfo=None) if getattr(archived_at, "tzinfo", None) else archived_at
        age_days = max(0, (now_naive - archived_naive).days)
        recycle_oldest_days = age_days if recycle_oldest_days is None else max(recycle_oldest_days, age_days)
    counts = _container_counts(db)
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="inbox_containers",
        screen_title="Inbox containers",
        screen_data={
            "active_tab": active_tab,
            "learning_count": counts.get(INBOX_INTENT_LEARN_EXPLORE, 0),
            "enjoy_count": counts.get(INBOX_INTENT_ENJOY_RECOVER, 0),
            "parked_count": counts.get(INBOX_INTENT_PARK_LET_GO, 0),
            "recycle_count": counts.get("recycle_bin", 0),
        },
        db=db,
    )
    return templates.TemplateResponse(
        request,
        "inbox_containers.html",
        {
            "request": request,
            "active_tab": active_tab,
            "learning_items": learning_items,
            "enjoy_items": enjoy_items,
            "parked_items": parked_items,
            "recycle_items": recycle_items,
            "container_counts": counts,
            "recycle_retention_days": recycle_retention_days,
            "recycle_expired_count": recycle_expired_count,
            "recycle_oldest_days": recycle_oldest_days,
            "form_success": request.query_params.get("success"),
            "form_error": request.query_params.get("error"),
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/inbox/metrics")
def inbox_metrics(db: Session = Depends(get_db)):
    now_utc = utc_now()
    now_naive = now_utc.replace(tzinfo=None)
    seven_days_ago = now_naive - timedelta(days=7)
    fourteen_days_ago = now_naive - timedelta(days=14)
    thirty_days_ago = now_naive - timedelta(days=30)

    active_inbox_tasks = (
        db.query(Task.id, Task.created_at)
        .filter(
            Task.in_inbox.is_(True),
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .all()
    )
    inbox_total = len(active_inbox_tasks)
    age_0_7 = 0
    age_8_30 = 0
    age_30_plus = 0
    older_than_14 = 0
    for row in active_inbox_tasks:
        created_at = row.created_at
        if not created_at:
            continue
        naive_created = created_at.replace(tzinfo=None) if getattr(created_at, "tzinfo", None) else created_at
        if naive_created <= fourteen_days_ago:
            older_than_14 += 1
        if naive_created <= thirty_days_ago:
            age_30_plus += 1
        elif naive_created <= seven_days_ago:
            age_8_30 += 1
        else:
            age_0_7 += 1

    unprocessed_over_7_days = (
        db.query(func.count(Task.id))
        .filter(
            Task.in_inbox.is_(True),
            Task.status.in_(ACTIVE_TASK_STATUSES),
            Task.intake_container == INBOX_INTENT_UNPROCESSED,
            Task.created_at <= seven_days_ago,
        )
        .scalar()
    ) or 0

    processed_last_7_rows = (
        db.query(Task.intake_container, func.count(Task.id))
        .filter(
            Task.intake_processed_at.isnot(None),
            Task.intake_processed_at >= seven_days_ago,
            Task.intake_container != INBOX_INTENT_UNPROCESSED,
        )
        .group_by(Task.intake_container)
        .all()
    )
    processed_last_7_days = {
        container: count for container, count in processed_last_7_rows if container
    }

    return JSONResponse(
        {
            "ok": True,
            "generated_at": now_utc.isoformat(),
            "inbox_total": inbox_total,
            "inbox_older_than_14_days": older_than_14,
            "inbox_age_buckets": {
                "0_7_days": age_0_7,
                "8_30_days": age_8_30,
                "30_plus_days": age_30_plus,
            },
            "unprocessed_over_7_days": int(unprocessed_over_7_days),
            "processed_last_7_days": processed_last_7_days,
        }
    )
