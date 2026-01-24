import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    GuidanceEvent,
    GuidanceReminder,
    HealthEntry,
    HealthMetric,
    HealthMetricCategory,
    Project,
    ProjectStatus,
    RitualEntry,
    RitualType,
    Task,
    TaskStatus,
    WhenBucket,
    WaitingOn,
)
from ..security import csrf_protect, require_html_auth
from ..utils.coach import refine_nudge_text

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
    event = (
        db.query(GuidanceEvent)
        .filter(GuidanceEvent.code == "weekly_review_done", GuidanceEvent.created_at >= since_dt)
        .first()
    )
    if event:
        return True
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


def _waiting_followup_due(db: Session, today: date) -> bool:
    return (
        db.query(WaitingOn)
        .filter(
            (WaitingOn.last_followup.is_(None)) | (WaitingOn.last_followup <= today)
        )
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
    {
        "code": "waiting_followup",
        "title": "Waiting on follow-ups",
        "body": "You have OPPs waiting on someone. Set a follow-up date so it doesn’t drift.",
        "link_label": "Open Waiting On",
        "link_url": "/waiting",
        "period_start": lambda today: today,
        "done_check": lambda db, period_start, today: not _waiting_followup_due(db, today),
    },
]


def _rituals_since(db: Session, since: date) -> list[RitualEntry]:
    return (
        db.query(RitualEntry)
        .filter(RitualEntry.entry_date >= since)
        .order_by(RitualEntry.entry_date.desc())
        .all()
    )


def _ritual_day_map(entries: list[RitualEntry]) -> dict[date, dict[str, RitualEntry]]:
    grouped: dict[date, dict[str, RitualEntry]] = {}
    for entry in entries:
        day = entry.entry_date
        if day not in grouped:
            grouped[day] = {}
        grouped[day][entry.ritual_type.value if entry.ritual_type else ""] = entry
    return grouped


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _health_trends(
    db: Session,
    today: date,
    category: HealthMetricCategory,
    window_days: int = 7,
) -> tuple[list[str], list[str], int]:
    metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.category == category)
        .order_by(HealthMetric.name.asc())
        .all()
    )
    if not metrics:
        return [], [], 0
    metric_ids = [m.id for m in metrics]
    entries = (
        db.query(HealthEntry)
        .filter(HealthEntry.metric_id.in_(metric_ids))
        .order_by(HealthEntry.entry_date.asc())
        .all()
    )
    entries_by_metric: dict[int, list[HealthEntry]] = {m.id: [] for m in metrics}
    for entry in entries:
        entries_by_metric[entry.metric_id].append(entry)

    last_start = today - timedelta(days=window_days - 1)
    prev_start = today - timedelta(days=window_days * 2 - 1)
    prev_end = today - timedelta(days=window_days)

    down: list[str] = []
    up: list[str] = []
    recent_count = 0

    for metric in metrics:
        values = entries_by_metric.get(metric.id, [])
        if not values:
            continue
        recent_values = [e.value for e in values if e.entry_date >= last_start]
        recent_count += len(recent_values)
        last_values = recent_values
        prev_values = [
            e.value for e in values if prev_start <= e.entry_date <= prev_end
        ]
        if len(last_values) < 2 or len(prev_values) < 2:
            continue
        last_avg = _avg(last_values)
        prev_avg = _avg(prev_values)
        if last_avg is None or prev_avg is None or prev_avg == 0:
            continue
        direction = metric.target_direction or "higher"
        ratio = last_avg / prev_avg
        if direction == "higher":
            if ratio <= 0.9:
                down.append(metric.name)
            elif ratio >= 1.1:
                up.append(metric.name)
        elif direction == "lower":
            if ratio >= 1.1:
                down.append(metric.name)
            elif ratio <= 0.9:
                up.append(metric.name)
    return down, up, recent_count


def _pattern_candidates(db: Session, today: date) -> list[dict[str, object]]:
    patterns: list[dict[str, object]] = []
    now = datetime.utcnow()

    ritual_entries = _rituals_since(db, today - timedelta(days=6))
    ritual_by_day = _ritual_day_map(ritual_entries)

    morning_entries = [e for e in ritual_entries if e.ritual_type == RitualType.MORNING]
    midday_entries = [e for e in ritual_entries if e.ritual_type == RitualType.MIDDAY]

    overbooked_count = sum(1 for e in morning_entries if e.focus_time_status == "overbooked")
    if overbooked_count >= 2:
        body = (
            f"You marked focus time as overbooked on {overbooked_count} of the last 7 mornings. "
            "Want to cut today down to 1–3 must‑dos and protect one focus block?"
        )
        patterns.append(
            {
                "code": "pattern_overbooked",
                "title": "Too much on the plate?",
                "body": body,
                "link_label": "Open morning ritual",
                "link_url": "/ritual/morning",
                "cooldown_hours": 18,
                "priority": 3,
                "tone": "watch",
            }
        )

    drift_count = sum(
        1
        for e in midday_entries
        if (e.midday_alignment or "") in {"off_track", "adjusting"}
    )
    if drift_count >= 3:
        body = (
            f"Midday check‑ins show you’re off track or adjusting {drift_count} times this week. "
            "Want a smaller One Thing and a single recovery block?"
        )
        patterns.append(
            {
                "code": "pattern_midday_drift",
                "title": "Midday drift pattern",
                "body": body,
                "link_label": "Open midday reset",
                "link_url": "/ritual/midday",
                "cooldown_hours": 24,
                "priority": 2,
                "tone": "watch",
            }
        )

    today_tasks_count = (
        db.query(Task)
        .filter(Task.when_bucket == WhenBucket.TODAY)
        .filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
        .count()
    )
    if today_tasks_count >= 8:
        body = (
            f"There are {today_tasks_count} tasks in Today. "
            "Want to trim to your One Thing + 2 support tasks?"
        )
        patterns.append(
            {
                "code": "pattern_too_many_today",
                "title": "Today is overloaded",
                "body": body,
                "link_label": "Open Tasks",
                "link_url": "/tasks/time",
                "cooldown_hours": 18,
                "priority": 3,
                "tone": "watch",
            }
        )

    frog_cutoff = now - timedelta(days=7)
    frog_tasks = (
        db.query(Task)
        .filter(Task.frog.is_(True))
        .filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
        .filter(Task.created_at <= frog_cutoff)
        .count()
    )
    if frog_tasks >= 2:
        body = (
            f"{frog_tasks} frog tasks have been open for over a week. "
            "Want to break one into a 15‑minute starter chunk?"
        )
        patterns.append(
            {
                "code": "pattern_frog_stall",
                "title": "Frog avoidance",
                "body": body,
                "link_label": "Open Tasks",
                "link_url": "/tasks/time",
                "cooldown_hours": 24,
                "priority": 3,
                "tone": "watch",
            }
        )

    stale_cutoff = now - timedelta(days=3)
    inbox_stale = (
        db.query(Task)
        .filter(Task.in_inbox.is_(True))
        .filter(Task.archived_from_inbox.is_(False))
        .filter(Task.created_at <= stale_cutoff)
        .count()
    )
    if inbox_stale >= 5:
        body = (
            f"There are {inbox_stale} inbox items older than 3 days. "
            "Quick sweep: decide task vs project for the top 3?"
        )
        patterns.append(
            {
                "code": "pattern_inbox_backlog",
                "title": "Inbox backlog",
                "body": body,
                "link_label": "Open Inbox",
                "link_url": "/",
                "cooldown_hours": 18,
                "priority": 2,
                "tone": "watch",
            }
        )

    aging_cutoff = now - timedelta(days=1)
    today_backlog = (
        db.query(Task)
        .filter(Task.when_bucket == WhenBucket.TODAY)
        .filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
        .filter(Task.created_at <= aging_cutoff)
        .count()
    )
    if today_backlog >= 3:
        body = (
            f"{today_backlog} Today tasks are still open from earlier days. "
            "Want to reschedule the non‑essentials to Week?"
        )
        patterns.append(
            {
                "code": "pattern_today_backlog",
                "title": "Today is carrying over",
                "body": body,
                "link_label": "Open Tasks",
                "link_url": "/tasks/time",
                "cooldown_hours": 24,
                "priority": 2,
                "tone": "watch",
            }
        )

    fitness_down, fitness_up, fitness_recent = _health_trends(
        db, today, HealthMetricCategory.FITNESS
    )
    strength_down, strength_up, strength_recent = _health_trends(
        db, today, HealthMetricCategory.STRENGTH
    )

    if not fitness_recent and not strength_recent:
        body = (
            "I haven’t seen fitness or strength entries in the last week. "
            "Want to log one quick metric to get momentum back?"
        )
        patterns.append(
            {
                "code": "pattern_health_gap",
                "title": "Fitness logging paused",
                "body": body,
                "link_label": "Open Health",
                "link_url": "/health",
                "cooldown_hours": 48,
                "priority": 1,
                "tone": "watch",
            }
        )
    else:
        if fitness_down:
            names = ", ".join(fitness_down[:2])
            body = (
                f"Fitness trends are dipping (e.g., {names}). "
                "Want to protect one easy movement block this week?"
            )
            patterns.append(
                {
                    "code": "pattern_fitness_down",
                    "title": "Fitness trending down",
                    "body": body,
                    "link_label": "Open Fitness",
                    "link_url": "/health/fitness",
                    "cooldown_hours": 72,
                    "priority": 1,
                    "tone": "watch",
                }
            )
        if strength_down:
            names = ", ".join(strength_down[:2])
            body = (
                f"Strength signals look softer (e.g., {names}). "
                "Want to schedule one short strength session?"
            )
            patterns.append(
                {
                    "code": "pattern_strength_down",
                    "title": "Strength trending down",
                    "body": body,
                    "link_label": "Open Strength",
                    "link_url": "/health/strength",
                    "cooldown_hours": 72,
                    "priority": 1,
                    "tone": "watch",
                }
            )
        if fitness_up or strength_up:
            names = ", ".join((fitness_up + strength_up)[:2])
            body = (
                f"Nice trend lift lately ({names}). "
                "Want to lock in the habit that’s working?"
            )
            patterns.append(
                {
                    "code": "pattern_health_up",
                    "title": "Momentum building",
                    "body": body,
                    "link_label": "Open Health",
                    "link_url": "/health",
                    "cooldown_hours": 168,
                    "priority": 0,
                    "tone": "praise",
                    "auto_complete": True,
                }
            )

    all_days = sorted(ritual_by_day.keys())
    complete_days = 0
    for day in all_days:
        day_entries = ritual_by_day[day]
        if {"morning", "midday", "evening"}.issubset(day_entries.keys()):
            complete_days += 1
    if all_days:
        if complete_days <= 1:
            body = (
                "Rituals have been sparse this week. "
                "Want a 3‑minute morning check‑in to restart the rhythm?"
            )
            patterns.append(
                {
                    "code": "pattern_ritual_slip",
                    "title": "Rituals slipping",
                    "body": body,
                    "link_label": "Open morning ritual",
                    "link_url": "/ritual/morning",
                    "cooldown_hours": 48,
                    "priority": 1,
                    "tone": "watch",
                }
            )
        elif complete_days >= 4:
            body = (
                f"You’ve completed all three check‑ins on {complete_days} days this week. "
                "That consistency is doing work."
            )
            patterns.append(
                {
                    "code": "pattern_ritual_streak",
                    "title": "Ritual streak",
                    "body": body,
                    "link_label": "Open morning ritual",
                    "link_url": "/ritual/morning",
                    "cooldown_hours": 168,
                    "priority": 0,
                    "tone": "praise",
                    "auto_complete": True,
                }
            )

    return patterns


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

    pattern_defs: dict[str, dict[str, object]] = {}
    pattern_candidates = _pattern_candidates(db, today)
    if pattern_candidates:
        watch = [p for p in pattern_candidates if p.get("tone") == "watch"]
        praise = [p for p in pattern_candidates if p.get("tone") == "praise"]
        watch.sort(key=lambda p: p.get("priority", 0), reverse=True)
        praise.sort(key=lambda p: p.get("priority", 0), reverse=True)
        selected = watch[:2] + praise[:1]
        for pattern in selected:
            code = pattern["code"]
            cooldown_hours = int(pattern.get("cooldown_hours", 24))
            cooldown = timedelta(hours=cooldown_hours)
            pattern_title = str(pattern["title"])
            pattern_body = str(pattern["body"])
            reminder = (
                db.query(GuidanceReminder)
                .filter(GuidanceReminder.code == code, GuidanceReminder.completed_at.is_(None))
                .order_by(GuidanceReminder.id.desc())
                .first()
            )
            if reminder is None:
                reminder = GuidanceReminder(
                    code=code,
                    title=pattern_title,
                    body=refine_nudge_text(pattern_body),
                    period_start=today,
                    due_on=today,
                )
                db.add(reminder)
                dirty = True
            else:
                if reminder.title != pattern_title or reminder.body != pattern_body:
                    reminder.title = pattern_title
                    reminder.body = pattern_body
                    dirty = True
            if reminder.snoozed_until and reminder.snoozed_until > now:
                continue
            if reminder.last_shown_at and now - reminder.last_shown_at < cooldown:
                continue
            reminder.last_shown_at = now
            reminders.append(reminder)
            pattern_defs[code] = {
                "link_label": pattern.get("link_label"),
                "link_url": pattern.get("link_url"),
                "auto_complete": pattern.get("auto_complete", False),
            }
            dirty = True

    if dirty:
        db.commit()

    payload = []
    for reminder in reminders:
        definition = next((d for d in REMINDER_DEFS if d["code"] == reminder.code), None)
        pattern_def = pattern_defs.get(reminder.code, {})
        payload.append(
            {
                "id": reminder.id,
                "code": reminder.code,
                "title": reminder.title,
                "body": reminder.body,
                "link_label": pattern_def.get("link_label")
                if pattern_def
                else definition.get("link_label") if definition else None,
                "link_url": pattern_def.get("link_url")
                if pattern_def
                else definition.get("link_url") if definition else None,
            }
        )
        if pattern_def.get("auto_complete"):
            reminder.completed_at = reminder.completed_at or now
            reminder.acknowledged_at = reminder.acknowledged_at or reminder.completed_at
            dirty = True

    if dirty:
        db.commit()

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
