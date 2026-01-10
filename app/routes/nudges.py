import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import GuidanceEvent, GuidanceReminder, Project, ProjectStatus, RitualEntry
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _start_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _start_of_month(day: date) -> date:
    return day.replace(day=1)


def _start_of_quarter(day: date) -> date:
    month = ((day.month - 1) // 3) * 3 + 1
    return date(day.year, month, 1)


def _start_of_year(day: date) -> date:
    return date(day.year, 1, 1)


def _end_of_month(day: date) -> date:
    next_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _end_of_quarter(day: date) -> date:
    start = _start_of_quarter(day)
    next_month = start.month + 3
    if next_month > 12:
        next_start = date(start.year + 1, 1, 1)
    else:
        next_start = date(start.year, next_month, 1)
    return next_start - timedelta(days=1)


def _project_updated_since(db: Session, since: date, horizon: str | None = None) -> bool:
    since_dt = datetime.combine(since, time.min)
    query = db.query(Project).filter(Project.status != ProjectStatus.ARCHIVED)
    if horizon:
        query = query.filter(Project.time_horizon == horizon)
    query = query.filter(func.coalesce(Project.updated_at, Project.created_at) >= since_dt)
    return query.first() is not None


def _weekly_review_done(db: Session, period_start: date) -> bool:
    since_dt = datetime.combine(period_start, time.min)
    query = (
        db.query(Project)
        .filter(Project.status != ProjectStatus.ARCHIVED)
        .filter(Project.active_this_week.is_(True))
        .filter(func.coalesce(Project.updated_at, Project.created_at) >= since_dt)
    )
    return query.first() is not None


def _daily_checkin_done(db: Session, today: date) -> bool:
    return (
        db.query(RitualEntry)
        .filter(RitualEntry.entry_date == today)
        .first()
        is not None
    )


def _window_start_for(code: str, today: date, period_start: date) -> date:
    if code == "weekly_review":
        return period_start + timedelta(days=4)
    if code == "monthly_focus":
        return _end_of_month(today) - timedelta(days=4)
    if code == "quarterly_pass":
        return _end_of_quarter(today) - timedelta(days=13)
    if code == "annual_reset":
        return date(today.year, 12, 1)
    return today


REMINDER_DEFS = [
    {
        "code": "annual_reset",
        "title": "Annual reset",
        "body": "Month before the year starts. Name 1-3 bets that matter in five years.",
        "link_label": "Open project pyramid",
        "link_url": "/long-term/pyramid",
        "period_start": _start_of_year,
        "done_check": lambda db, period_start, today: _project_updated_since(db, period_start, "year"),
    },
    {
        "code": "quarterly_pass",
        "title": "Quarterly pass",
        "body": "Weekend before the quarter. Update the project pyramid and trim the list.",
        "link_label": "Open project pyramid",
        "link_url": "/long-term/pyramid",
        "period_start": _start_of_quarter,
        "done_check": lambda db, period_start, today: _project_updated_since(db, period_start, "quarter"),
    },
    {
        "code": "monthly_focus",
        "title": "Monthly focus",
        "body": "Weekend before the month or first Monday. Budget focus blocks.",
        "link_label": "Open project pyramid",
        "link_url": "/long-term/pyramid",
        "period_start": _start_of_month,
        "done_check": lambda db, period_start, today: _project_updated_since(db, period_start, "month"),
    },
    {
        "code": "weekly_review",
        "title": "Weekly review",
        "body": "Sunday night or Monday morning. Curate 4 work + 3 personal projects.",
        "link_label": "Open weekly review",
        "link_url": "/weekly",
        "period_start": _start_of_week,
        "done_check": lambda db, period_start, today: _weekly_review_done(db, period_start),
    },
    {
        "code": "daily_checkin",
        "title": "Daily check-in",
        "body": "Night before or first thing. Protect your One Thing before OPP.",
        "link_label": "Open morning ritual",
        "link_url": "/ritual/morning",
        "period_start": lambda today: today,
        "done_check": lambda db, period_start, today: _daily_checkin_done(db, today),
    },
]


@router.get("/nudges")
def list_nudges(db: Session = Depends(get_db)):
    today = date.today()
    now = datetime.utcnow()
    reminders: list[GuidanceReminder] = []
    dirty = False

    for definition in REMINDER_DEFS:
        code = definition["code"]
        period_start = definition["period_start"](today)
        window_start = _window_start_for(code, today, period_start)

        reminder = (
            db.query(GuidanceReminder)
            .filter(GuidanceReminder.code == code, GuidanceReminder.period_start == period_start)
            .order_by(GuidanceReminder.id.desc())
            .first()
        )

        if reminder and reminder.completed_at:
            continue

        if reminder is None:
            if today < window_start:
                continue
            reminder = GuidanceReminder(
                code=code,
                title=definition["title"],
                body=definition["body"],
                period_start=period_start,
                due_on=window_start,
            )
            db.add(reminder)
            dirty = True
        else:
            if reminder.title != definition["title"] or reminder.body != definition["body"]:
                reminder.title = definition["title"]
                reminder.body = definition["body"]
                dirty = True

        done_check = definition["done_check"]
        if done_check(db, period_start, today):
            if reminder.completed_at is None:
                reminder.completed_at = now
                reminder.acknowledged_at = reminder.acknowledged_at or reminder.completed_at
                dirty = True
            continue

        if code == "daily_checkin" and period_start < today:
            reminder.completed_at = now
            dirty = True
            continue

        if reminder.snoozed_until and reminder.snoozed_until > now:
            continue

        reminder.last_shown_at = now
        reminders.append(reminder)
        dirty = True

    if dirty:
        db.commit()

    payload = []
    for reminder in reminders:
        definition = next((d for d in REMINDER_DEFS if d["code"] == reminder.code), None)
        payload.append(
            {
                "id": reminder.id,
                "code": reminder.code,
                "title": reminder.title,
                "body": reminder.body,
                "link_label": definition.get("link_label") if definition else None,
                "link_url": definition.get("link_url") if definition else None,
            }
        )

    return JSONResponse({"nudges": payload})


@router.post("/nudges/{reminder_id}/complete")
def complete_nudge(reminder_id: int, db: Session = Depends(get_db)):
    reminder = db.get(GuidanceReminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    now = datetime.utcnow()
    reminder.completed_at = reminder.completed_at or now
    reminder.acknowledged_at = reminder.acknowledged_at or now
    reminder.snoozed_until = None
    db.add(reminder)
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/nudges/{reminder_id}/snooze")
async def snooze_nudge(reminder_id: int, request: Request, db: Session = Depends(get_db)):
    reminder = db.get(GuidanceReminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    minutes = payload.get("minutes")
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid snooze duration")

    if minutes <= 0 or minutes > 60 * 24 * 14:
        raise HTTPException(status_code=400, detail="Invalid snooze duration")

    reminder.snoozed_until = datetime.utcnow() + timedelta(minutes=minutes)
    reminder.last_shown_at = datetime.utcnow()
    db.add(reminder)
    db.commit()
    return JSONResponse({"ok": True, "snoozed_until": reminder.snoozed_until.isoformat()})


@router.post("/nudges/displacement/ack")
async def acknowledge_displacement(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    context = {
        "capture_kind": (payload.get("capture_kind") or "").strip() or None,
        "title": (payload.get("title") or "").strip() or None,
    }
    context_json = json.dumps(context, ensure_ascii=True)
    event = GuidanceEvent(code="displacement_check", context_json=context_json)
    db.add(event)
    db.commit()
    return JSONResponse({"ok": True})
