from __future__ import annotations

from datetime import date, datetime, timedelta
import json
from typing import Iterable
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    HealthEntry,
    HealthExerciseSession,
    HealthGoal,
    HealthMetric,
    HealthMetricCategory,
    HealthSupplement,
    HealthTrainingPlan,
    HealthTrainingSetLog,
)
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])

SUPPLEMENT_TIMING_OPTIONS = (
    "morning",
    "midday",
    "evening",
    "bedtime",
    "with_meals",
    "custom",
)

EXERCISE_DAY_OPTIONS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

EXERCISE_FOCUS_OPTIONS = (
    "fitness",
    "strength",
    "flexibility",
)

EXERCISE_FOCUS_LINKS: dict[str, dict[str, str]] = {
    "fitness": {"path": "/health/fitness", "label": "Fitness log"},
    "strength": {"path": "/health/strength", "label": "Strength log"},
    "flexibility": {"path": "/health/flexibility", "label": "Flexibility log"},
}

TRACKER_TABS = (
    {
        "key": "diet",
        "label": "Diet",
        "path": "/health/diet",
        "description": "Nutrition and fueling quality trends.",
        "categories": (HealthMetricCategory.DIET,),
    },
    {
        "key": "weight",
        "label": "Weight",
        "path": "/health/weight",
        "description": "Body composition and blood pressure markers.",
        "categories": (HealthMetricCategory.WEIGHT, HealthMetricCategory.VITALS),
    },
    {
        "key": "fitness",
        "label": "Fitness",
        "path": "/health/fitness",
        "description": "Endurance, conditioning, and recovery load.",
        "categories": (HealthMetricCategory.FITNESS, HealthMetricCategory.RECOVERY),
    },
    {
        "key": "strength",
        "label": "Strength",
        "path": "/health/strength",
        "description": "Strength progression and output.",
        "categories": (HealthMetricCategory.STRENGTH,),
    },
    {
        "key": "flexibility",
        "label": "Flexibility",
        "path": "/health/flexibility",
        "description": "Mobility and movement quality.",
        "categories": (HealthMetricCategory.FLEXIBILITY,),
    },
)

TRACKER_NAV_ITEMS = tuple(
    {"key": tab["key"], "label": tab["label"], "path": tab["path"]} for tab in TRACKER_TABS
)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _safe_redirect(path: str | None, fallback: str = "/health") -> str:
    if not path or not path.startswith("/health"):
        return fallback
    return path


def _normalize_supplement_timing(value: str | None) -> str:
    if not value:
        return "morning"
    normalized = value.strip().lower()
    return normalized if normalized in SUPPLEMENT_TIMING_OPTIONS else "custom"


def _normalize_exercise_day(value: str | None) -> str:
    if not value:
        return "monday"
    normalized = value.strip().lower()
    return normalized if normalized in EXERCISE_DAY_OPTIONS else "monday"


def _normalize_exercise_focus(value: str | None) -> str:
    if not value:
        return "fitness"
    normalized = value.strip().lower()
    return normalized if normalized in EXERCISE_FOCUS_OPTIONS else "fitness"


def _parse_duration_minutes(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        parsed = int(cleaned)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return min(parsed, 600)


def _parse_positive_int(value: str | None, *, max_value: int = 9999) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        parsed = int(cleaned)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return min(parsed, max_value)


def _parse_time_value(value: str | None):
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%H:%M").time()
    except ValueError:
        return None


def _safe_int(value: str | None) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return cleaned or "metric"


def _fetch_entries(
    db: Session,
    metric_ids: Iterable[int],
    limit: int = 30,
) -> dict[int, list[HealthEntry]]:
    ids = list(metric_ids)
    entries_by_metric = {metric_id: [] for metric_id in ids}
    if not ids:
        return entries_by_metric
    rows = (
        db.query(HealthEntry)
        .filter(HealthEntry.metric_id.in_(ids))
        .order_by(HealthEntry.entry_date.asc(), HealthEntry.created_at.asc())
        .all()
    )
    for row in rows:
        entries_by_metric[row.metric_id].append(row)
    if limit:
        for metric_id in ids:
            entries = entries_by_metric[metric_id]
            if len(entries) > limit:
                entries_by_metric[metric_id] = entries[-limit:]
    return entries_by_metric


def _latest_entries(entries_by_metric: dict[int, list[HealthEntry]]) -> dict[int, HealthEntry]:
    latest: dict[int, HealthEntry] = {}
    for metric_id, entries in entries_by_metric.items():
        if entries:
            latest[metric_id] = entries[-1]
    return latest


def _metric_by_slug(db: Session, slug: str) -> HealthMetric | None:
    return db.query(HealthMetric).filter(HealthMetric.slug == slug).first()


def _json_payload(data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=True)
    return payload.replace("</", "<\\/")


def _metric_stats(entries_by_metric: dict[int, list[HealthEntry]]) -> dict[int, dict[str, float | None]]:
    stats: dict[int, dict[str, float | None]] = {}
    cutoff = date.today() - timedelta(days=6)
    for metric_id, entries in entries_by_metric.items():
        recent_values = [entry.value for entry in entries if entry.entry_date >= cutoff]
        avg_7d = sum(recent_values) / len(recent_values) if recent_values else None
        trend = None
        if len(entries) >= 2:
            trend = entries[-1].value - entries[-2].value
        stats[metric_id] = {"avg_7d": avg_7d, "trend": trend}
    return stats


def _category_metrics(db: Session, categories: Iterable[HealthMetricCategory]) -> list[HealthMetric]:
    return (
        db.query(HealthMetric)
        .filter(HealthMetric.category.in_(list(categories)))
        .order_by(HealthMetric.name.asc())
        .all()
    )


def _recent_entries(
    db: Session,
    categories: Iterable[HealthMetricCategory],
    limit: int = 14,
) -> list[HealthEntry]:
    return (
        db.query(HealthEntry)
        .join(HealthMetric, HealthEntry.metric_id == HealthMetric.id)
        .filter(HealthMetric.category.in_(list(categories)))
        .order_by(HealthEntry.entry_date.desc(), HealthEntry.created_at.desc())
        .limit(limit)
        .all()
    )


def _tracker_cards(db: Session) -> list[dict[str, object]]:
    week_cutoff = date.today() - timedelta(days=6)
    cards: list[dict[str, object]] = []
    for tab in TRACKER_TABS:
        categories = tab["categories"]
        metrics = _category_metrics(db, categories)
        metric_ids = [metric.id for metric in metrics]
        recent_entries_count = 0
        latest_entry_date = None
        if metric_ids:
            recent_entries_count = (
                db.query(HealthEntry)
                .filter(
                    HealthEntry.metric_id.in_(metric_ids),
                    HealthEntry.entry_date >= week_cutoff,
                )
                .count()
            )
            latest_entry = (
                db.query(HealthEntry)
                .filter(HealthEntry.metric_id.in_(metric_ids))
                .order_by(HealthEntry.entry_date.desc(), HealthEntry.created_at.desc())
                .first()
            )
            latest_entry_date = latest_entry.entry_date if latest_entry else None
        cards.append(
            {
                "key": tab["key"],
                "label": tab["label"],
                "path": tab["path"],
                "description": tab["description"],
                "metric_count": len(metrics),
                "recent_entries_count": recent_entries_count,
                "latest_entry_date": latest_entry_date,
            }
        )
    return cards


@router.post("/health/entry")
def add_health_entry(
    metric_id: int = Form(...),
    value: str = Form(...),
    entry_date: str | None = Form(None),
    notes: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    metric = db.get(HealthMetric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    parsed_value = _parse_float(value)
    if parsed_value is None:
        return RedirectResponse(
            url=f"{_safe_redirect(return_to)}?error=Enter+a+valid+number.",
            status_code=303,
        )

    parsed_date = _parse_date(entry_date) or date.today()
    entry = HealthEntry(
        metric_id=metric_id,
        value=parsed_value,
        entry_date=parsed_date,
        notes=notes.strip() if notes else None,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse(url=_safe_redirect(return_to), status_code=303)


@router.post("/health/goals")
def add_health_goal(
    title: str = Form(...),
    metric_id: str | None = Form(""),
    target_value: str | None = Form(None),
    target_date: str | None = Form(None),
    notes: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    cleaned_title = title.strip()
    if not cleaned_title:
        return RedirectResponse(
            url=f"{_safe_redirect(return_to)}?error=Goal+title+is+required.",
            status_code=303,
        )

    parsed_metric_id = int(metric_id) if metric_id not in (None, "", "null") else None
    parsed_target = _parse_float(target_value)
    parsed_date = _parse_date(target_date)

    goal = HealthGoal(
        title=cleaned_title,
        metric_id=parsed_metric_id,
        target_value=parsed_target,
        target_date=parsed_date,
        notes=notes.strip() if notes else None,
    )
    db.add(goal)
    db.commit()
    return RedirectResponse(url=_safe_redirect(return_to), status_code=303)


@router.post("/health/supplements")
def add_health_supplement(
    name: str = Form(...),
    dose: str | None = Form(None),
    timing: str = Form("morning"),
    timing_detail: str | None = Form(None),
    notes: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    cleaned_name = name.strip()
    if not cleaned_name:
        return RedirectResponse(
            url=f"{_safe_redirect(return_to)}?error=Supplement+name+is+required.",
            status_code=303,
        )
    normalized_timing = _normalize_supplement_timing(timing)
    detail = timing_detail.strip() if timing_detail else None
    supplement = HealthSupplement(
        name=cleaned_name,
        dose=dose.strip() if dose else None,
        timing=normalized_timing,
        timing_detail=detail or None,
        notes=notes.strip() if notes else None,
        is_active=True,
    )
    db.add(supplement)
    db.commit()
    return RedirectResponse(url=_safe_redirect(return_to), status_code=303)


@router.post("/health/supplements/deactivate")
def deactivate_health_supplement(
    supplement_id: int = Form(...),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    supplement = db.get(HealthSupplement, supplement_id)
    if not supplement:
        raise HTTPException(status_code=404, detail="Supplement not found")
    supplement.is_active = False
    db.add(supplement)
    db.commit()
    return RedirectResponse(url=_safe_redirect(return_to), status_code=303)


@router.post("/health/exercise/sessions")
def add_health_exercise_session(
    day_of_week: str = Form("monday"),
    focus_area: str = Form("fitness"),
    title: str = Form(...),
    start_time: str | None = Form(None),
    duration_minutes: str | None = Form(None),
    notes: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    safe_return = _safe_redirect(return_to, fallback="/health/exercise")
    cleaned_title = title.strip()
    if not cleaned_title:
        return RedirectResponse(
            url=f"{safe_return}?error=Session+title+is+required.",
            status_code=303,
        )

    parsed_duration = _parse_duration_minutes(duration_minutes)
    if duration_minutes and duration_minutes.strip() and parsed_duration is None:
        return RedirectResponse(
            url=f"{safe_return}?error=Duration+must+be+a+positive+number.",
            status_code=303,
        )

    parsed_time = _parse_time_value(start_time)
    if start_time and start_time.strip() and parsed_time is None:
        return RedirectResponse(
            url=f"{safe_return}?error=Start+time+must+use+HH:MM.",
            status_code=303,
        )

    session = HealthExerciseSession(
        day_of_week=_normalize_exercise_day(day_of_week),
        focus_area=_normalize_exercise_focus(focus_area),
        title=cleaned_title,
        start_time=parsed_time,
        duration_minutes=parsed_duration,
        notes=notes.strip() if notes else None,
        is_active=True,
    )
    db.add(session)
    db.commit()
    return RedirectResponse(url=safe_return, status_code=303)


@router.post("/health/exercise/sessions/deactivate")
def deactivate_health_exercise_session(
    session_id: int = Form(...),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    session = db.get(HealthExerciseSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Exercise session not found")
    session.is_active = False
    db.add(session)
    db.commit()
    return RedirectResponse(url=_safe_redirect(return_to, fallback="/health/exercise"), status_code=303)


@router.post("/health/training/plans")
def save_health_training_plan(
    title: str = Form(...),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    focus_goal: str | None = Form(None),
    notes: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    safe_return = _safe_redirect(return_to, fallback="/health/training")
    cleaned_title = title.strip()
    if not cleaned_title:
        return RedirectResponse(
            url=f"{safe_return}?error=Plan+title+is+required.",
            status_code=303,
        )
    parsed_start = _parse_date(start_date)
    parsed_end = _parse_date(end_date)
    if parsed_start and parsed_end and parsed_end < parsed_start:
        return RedirectResponse(
            url=f"{safe_return}?error=Plan+end+date+must+be+on+or+after+start+date.",
            status_code=303,
        )

    active_plans = (
        db.query(HealthTrainingPlan).filter(HealthTrainingPlan.is_active.is_(True)).all()
    )
    for active in active_plans:
        active.is_active = False
        db.add(active)

    new_plan = HealthTrainingPlan(
        title=cleaned_title,
        start_date=parsed_start,
        end_date=parsed_end,
        focus_goal=focus_goal.strip() if focus_goal else None,
        notes=notes.strip() if notes else None,
        is_active=True,
    )
    db.add(new_plan)
    db.commit()
    return RedirectResponse(url=safe_return, status_code=303)


@router.post("/health/training/sets")
def add_health_training_set_log(
    session_id: str | None = Form(""),
    exercise_name: str | None = Form(None),
    reps: str | None = Form(None),
    load_text: str | None = Form(None),
    duration_seconds: str | None = Form(None),
    notes: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    safe_return = _safe_redirect(return_to, fallback="/health/training")
    parsed_session_id = _safe_int(session_id)
    linked_session = None
    if parsed_session_id is not None:
        linked_session = db.get(HealthExerciseSession, parsed_session_id)
        if linked_session is None:
            return RedirectResponse(
                url=f"{safe_return}?error=Selected+session+was+not+found.",
                status_code=303,
            )

    parsed_reps = _parse_positive_int(reps, max_value=5000)
    if reps and reps.strip() and parsed_reps is None:
        return RedirectResponse(
            url=f"{safe_return}?error=Reps+must+be+a+positive+number.",
            status_code=303,
        )

    parsed_seconds = _parse_positive_int(duration_seconds, max_value=7200)
    if duration_seconds and duration_seconds.strip() and parsed_seconds is None:
        return RedirectResponse(
            url=f"{safe_return}?error=Duration+seconds+must+be+a+positive+number.",
            status_code=303,
        )

    if parsed_reps is None and parsed_seconds is None:
        return RedirectResponse(
            url=f"{safe_return}?error=Log+at+least+reps+or+duration.",
            status_code=303,
        )

    cleaned_exercise = exercise_name.strip() if exercise_name else None
    if not cleaned_exercise and linked_session is not None:
        cleaned_exercise = linked_session.title

    new_log = HealthTrainingSetLog(
        session_id=linked_session.id if linked_session else None,
        log_date=date.today(),
        exercise_name=cleaned_exercise or None,
        reps=parsed_reps,
        load_text=load_text.strip() if load_text else None,
        duration_seconds=parsed_seconds,
        notes=notes.strip() if notes else None,
    )
    db.add(new_log)
    db.commit()
    return RedirectResponse(url=safe_return, status_code=303)


@router.post("/health/blood-pressure")
def add_blood_pressure(
    systolic: str = Form(...),
    diastolic: str = Form(...),
    entry_date: str | None = Form(None),
    notes: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    systolic_value = _parse_float(systolic)
    diastolic_value = _parse_float(diastolic)
    if systolic_value is None or diastolic_value is None:
        return RedirectResponse(
            url=f"{_safe_redirect(return_to)}?error=Enter+both+blood+pressure+values.",
            status_code=303,
        )

    systolic_metric = _metric_by_slug(db, "bp_systolic")
    diastolic_metric = _metric_by_slug(db, "bp_diastolic")
    if not systolic_metric or not diastolic_metric:
        return RedirectResponse(
            url=f"{_safe_redirect(return_to)}?error=Blood+pressure+metrics+not+found.",
            status_code=303,
        )

    parsed_date = _parse_date(entry_date) or date.today()
    cleaned_notes = notes.strip() if notes else None
    entries = [
        HealthEntry(
            metric_id=systolic_metric.id,
            value=systolic_value,
            entry_date=parsed_date,
            notes=cleaned_notes,
        ),
        HealthEntry(
            metric_id=diastolic_metric.id,
            value=diastolic_value,
            entry_date=parsed_date,
            notes=cleaned_notes,
        ),
    ]
    db.add_all(entries)
    db.commit()
    return RedirectResponse(url=_safe_redirect(return_to), status_code=303)


@router.post("/health/metrics")
def add_health_metric(
    name: str = Form(...),
    unit: str | None = Form(None),
    category: str = Form(HealthMetricCategory.FITNESS.value),
    description: str | None = Form(None),
    target_direction: str | None = Form(None),
    return_to: str | None = Form(None),
    db: Session = Depends(get_db),
):
    cleaned_name = name.strip()
    if not cleaned_name:
        return RedirectResponse(
            url=f"{_safe_redirect(return_to)}?error=Metric+name+is+required.",
            status_code=303,
        )
    try:
        parsed_category = HealthMetricCategory(category)
    except ValueError:
        parsed_category = HealthMetricCategory.FITNESS

    base_slug = _slugify(cleaned_name)
    slug = base_slug
    idx = 1
    while db.query(HealthMetric).filter(HealthMetric.slug == slug).first():
        idx += 1
        slug = f"{base_slug}_{idx}"

    metric = HealthMetric(
        name=cleaned_name,
        slug=slug,
        category=parsed_category,
        unit=unit.strip() if unit else None,
        description=description.strip() if description else None,
        target_direction=target_direction.strip() if target_direction else None,
        is_key=False,
    )
    db.add(metric)
    db.commit()
    return RedirectResponse(url=_safe_redirect(return_to), status_code=303)


@router.get("/health", response_class=HTMLResponse)
def health_dashboard(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    key_metrics = (
        db.query(HealthMetric)
        .filter(HealthMetric.is_key.is_(True))
        .order_by(HealthMetric.name.asc())
        .all()
    )
    metric_ids = [metric.id for metric in key_metrics]
    entries_by_metric = _fetch_entries(db, metric_ids, limit=30)
    latest = _latest_entries(entries_by_metric)
    stats = _metric_stats(entries_by_metric)
    goals = db.query(HealthGoal).order_by(HealthGoal.target_date.asc().nulls_last()).all()
    all_metrics = db.query(HealthMetric).order_by(HealthMetric.name.asc()).all()
    entry_metrics = [
        metric for metric in all_metrics if metric.slug not in {"bp_systolic", "bp_diastolic"}
    ]

    series_payload = {
        str(metric_id): [
            {"date": entry.entry_date.isoformat(), "value": entry.value}
            for entry in entries_by_metric.get(metric_id, [])
        ]
        for metric_id in metric_ids
    }

    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="health_dashboard",
        screen_title="Health dashboard",
        screen_data={
            "key_metrics": [
                {
                    "id": metric.id,
                    "name": metric.name,
                    "unit": metric.unit,
                    "latest": latest.get(metric.id).value if metric.id in latest else None,
                }
                for metric in key_metrics
            ],
            "goals": [{"id": goal.id, "title": goal.title} for goal in goals],
        },
        db=db,
    )

    return templates.TemplateResponse(
        request,
        "health_dashboard.html",
        {
            "request": request,
            "active_health_tab": "dashboard",
            "active_health_primary": "dashboard",
            "key_metrics": key_metrics,
            "metric_latest": latest,
            "metric_stats": stats,
            "goals": goals,
            "health_series_json": _json_payload(series_payload),
            "form_error": request.query_params.get("error"),
            "coach_context_json": coach_context_json,
            "all_metrics": all_metrics,
            "entry_metrics": entry_metrics,
        },
    )


@router.get("/health/supplements", response_class=HTMLResponse)
def health_supplements(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    active_supplements = (
        db.query(HealthSupplement)
        .filter(HealthSupplement.is_active.is_(True))
        .order_by(HealthSupplement.name.asc(), HealthSupplement.created_at.asc())
        .all()
    )
    recent_inactive_supplements = (
        db.query(HealthSupplement)
        .filter(HealthSupplement.is_active.is_(False))
        .order_by(HealthSupplement.updated_at.desc().nulls_last(), HealthSupplement.created_at.desc())
        .limit(8)
        .all()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="health_supplements",
        screen_title="Health supplements",
        screen_data={
            "active_supplement_count": len(active_supplements),
            "recently_stopped_count": len(recent_inactive_supplements),
        },
        db=db,
    )

    return templates.TemplateResponse(
        request,
        "health_supplements.html",
        {
            "request": request,
            "active_health_tab": "supplements",
            "active_health_primary": "supplements",
            "active_supplements": active_supplements,
            "recent_inactive_supplements": recent_inactive_supplements,
            "supplement_timing_options": SUPPLEMENT_TIMING_OPTIONS,
            "form_error": request.query_params.get("error"),
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/health/exercise", response_class=HTMLResponse)
def health_exercise_plan(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    active_sessions = (
        db.query(HealthExerciseSession)
        .filter(HealthExerciseSession.is_active.is_(True))
        .all()
    )
    ordered_sessions = sorted(
        active_sessions,
        key=lambda item: (
            EXERCISE_DAY_OPTIONS.index(_normalize_exercise_day(item.day_of_week)),
            item.start_time.strftime("%H:%M") if item.start_time else "99:99",
            item.title.lower(),
        ),
    )
    sessions_by_day = []
    for day_key in EXERCISE_DAY_OPTIONS:
        day_sessions = [
            item
            for item in ordered_sessions
            if _normalize_exercise_day(item.day_of_week) == day_key
        ]
        sessions_by_day.append(
            {
                "day_key": day_key,
                "day_label": day_key.title(),
                "sessions": day_sessions,
            }
        )

    recent_inactive_sessions = (
        db.query(HealthExerciseSession)
        .filter(HealthExerciseSession.is_active.is_(False))
        .order_by(
            HealthExerciseSession.updated_at.desc().nulls_last(),
            HealthExerciseSession.created_at.desc(),
        )
        .limit(8)
        .all()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="health_exercise_plan",
        screen_title="Exercise plan",
        screen_data={
            "active_session_count": len(ordered_sessions),
            "day_count_with_sessions": sum(
                1 for row in sessions_by_day if row["sessions"]
            ),
        },
        db=db,
    )
    return templates.TemplateResponse(
        request,
        "health_exercise.html",
        {
            "request": request,
            "active_health_tab": "exercise",
            "active_health_primary": "exercise",
            "exercise_day_options": EXERCISE_DAY_OPTIONS,
            "exercise_focus_options": EXERCISE_FOCUS_OPTIONS,
            "exercise_focus_links": EXERCISE_FOCUS_LINKS,
            "sessions_by_day": sessions_by_day,
            "recent_inactive_sessions": recent_inactive_sessions,
            "form_error": request.query_params.get("error"),
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/health/training", response_class=HTMLResponse)
def health_training_live(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    today = date.today()
    today_key = today.strftime("%A").lower()
    form_error = request.query_params.get("error")
    show_plan_editor = bool(
        form_error and ("plan" in form_error.lower() or "date" in form_error.lower())
    )
    show_log_context = bool(
        form_error and ("session" in form_error.lower())
    )

    active_plan = (
        db.query(HealthTrainingPlan)
        .filter(HealthTrainingPlan.is_active.is_(True))
        .order_by(HealthTrainingPlan.created_at.desc())
        .first()
    )
    today_sessions = (
        db.query(HealthExerciseSession)
        .filter(
            HealthExerciseSession.is_active.is_(True),
            HealthExerciseSession.day_of_week == today_key,
        )
        .all()
    )
    today_sessions = sorted(
        today_sessions,
        key=lambda item: (
            item.start_time.strftime("%H:%M") if item.start_time else "99:99",
            item.title.lower(),
        ),
    )
    all_active_sessions = (
        db.query(HealthExerciseSession)
        .filter(HealthExerciseSession.is_active.is_(True))
        .all()
    )
    all_active_sessions = sorted(
        all_active_sessions,
        key=lambda item: (
            EXERCISE_DAY_OPTIONS.index(_normalize_exercise_day(item.day_of_week)),
            item.start_time.strftime("%H:%M") if item.start_time else "99:99",
            item.title.lower(),
        ),
    )
    weekly_grouped = []
    for day_key in EXERCISE_DAY_OPTIONS:
        sessions = [s for s in all_active_sessions if _normalize_exercise_day(s.day_of_week) == day_key]
        weekly_grouped.append(
            {
                "day_key": day_key,
                "day_label": day_key.title(),
                "sessions": sessions,
            }
        )

    today_logs = (
        db.query(HealthTrainingSetLog)
        .filter(HealthTrainingSetLog.log_date == today)
        .order_by(HealthTrainingSetLog.created_at.desc())
        .all()
    )
    session_ids = [row.session_id for row in today_logs if row.session_id is not None]
    session_lookup: dict[int, HealthExerciseSession] = {}
    if session_ids:
        linked_sessions = (
            db.query(HealthExerciseSession)
            .filter(HealthExerciseSession.id.in_(session_ids))
            .all()
        )
        session_lookup = {session.id: session for session in linked_sessions}

    total_reps = 0
    total_seconds = 0
    logs_view = []
    for row in today_logs:
        linked = session_lookup.get(row.session_id) if row.session_id else None
        if row.reps:
            total_reps += row.reps
        if row.duration_seconds:
            total_seconds += row.duration_seconds
        logs_view.append(
            {
                "id": row.id,
                "time_label": row.created_at.strftime("%I:%M %p").lstrip("0") if row.created_at else "",
                "session_title": linked.title if linked else None,
                "focus_area": linked.focus_area if linked else None,
                "exercise_name": row.exercise_name,
                "reps": row.reps,
                "load_text": row.load_text,
                "duration_seconds": row.duration_seconds,
                "notes": row.notes,
            }
        )

    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="health_training_live",
        screen_title="Training live",
        screen_data={
            "today_session_count": len(today_sessions),
            "today_log_count": len(logs_view),
            "has_active_plan": bool(active_plan),
        },
        db=db,
    )

    return templates.TemplateResponse(
        request,
        "health_training.html",
        {
            "request": request,
            "active_health_tab": "training",
            "active_health_primary": "training",
            "today_label": today.strftime("%A, %d %b %Y"),
            "active_plan": active_plan,
            "today_sessions": today_sessions,
            "weekly_grouped_sessions": weekly_grouped,
            "today_logs": logs_view,
            "today_totals": {
                "sets": len(logs_view),
                "reps": total_reps,
                "minutes": round(total_seconds / 60, 1) if total_seconds else 0,
            },
            "exercise_focus_links": EXERCISE_FOCUS_LINKS,
            "form_error": form_error,
            "show_plan_editor": show_plan_editor,
            "show_log_context": show_log_context,
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/health/trackers", response_class=HTMLResponse)
def health_trackers(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    cards = _tracker_cards(db)
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="health_trackers",
        screen_title="Health trackers",
        screen_data={
            "tracker_count": len(cards),
            "total_metrics": sum(int(card["metric_count"]) for card in cards),
        },
        db=db,
    )
    return templates.TemplateResponse(
        request,
        "health_trackers.html",
        {
            "request": request,
            "active_health_tab": "trackers",
            "active_health_primary": "trackers",
            "tracker_cards": cards,
            "form_error": request.query_params.get("error"),
            "coach_context_json": coach_context_json,
        },
    )


def _health_category_page(
    *,
    request: Request,
    db: Session,
    screen_id: str,
    screen_title: str,
    active_tab: str,
    categories: Iterable[HealthMetricCategory],
    template_name: str,
    exclude_entry_slugs: set[str] | None = None,
):
    templates = request.app.state.templates
    metrics = _category_metrics(db, categories)
    excluded = exclude_entry_slugs or set()
    entry_metrics = [metric for metric in metrics if metric.slug not in excluded]
    metric_ids = [metric.id for metric in metrics]
    entries_by_metric = _fetch_entries(db, metric_ids, limit=30)
    latest = _latest_entries(entries_by_metric)
    stats = _metric_stats(entries_by_metric)
    recent_entries = _recent_entries(db, categories, limit=12)
    series_payload = {
        str(metric_id): [
            {"date": entry.entry_date.isoformat(), "value": entry.value}
            for entry in entries_by_metric.get(metric_id, [])
        ]
        for metric_id in metric_ids
    }

    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id=screen_id,
        screen_title=screen_title,
        screen_data={
            "metric_count": len(metrics),
            "recent_entries": len(recent_entries),
        },
        db=db,
    )

    return templates.TemplateResponse(
        request,
        template_name,
        {
            "request": request,
            "active_health_tab": active_tab,
            "active_health_primary": "trackers",
            "active_tracker_tab": active_tab,
            "tracker_nav_items": TRACKER_NAV_ITEMS,
            "metrics": metrics,
            "entry_metrics": entry_metrics,
            "metric_latest": latest,
            "metric_stats": stats,
            "recent_entries": recent_entries,
            "health_series_json": _json_payload(series_payload),
            "form_error": request.query_params.get("error"),
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/health/diet", response_class=HTMLResponse)
def health_diet(request: Request, db: Session = Depends(get_db)):
    return _health_category_page(
        request=request,
        db=db,
        screen_id="health_diet",
        screen_title="Diet planning",
        active_tab="diet",
        categories=[HealthMetricCategory.DIET],
        template_name="health_diet.html",
    )


@router.get("/health/weight", response_class=HTMLResponse)
def health_weight(request: Request, db: Session = Depends(get_db)):
    return _health_category_page(
        request=request,
        db=db,
        screen_id="health_weight",
        screen_title="Weight and body composition",
        active_tab="weight",
        categories=[HealthMetricCategory.WEIGHT, HealthMetricCategory.VITALS],
        template_name="health_weight.html",
        exclude_entry_slugs={"bp_systolic", "bp_diastolic"},
    )


@router.get("/health/fitness", response_class=HTMLResponse)
def health_fitness(request: Request, db: Session = Depends(get_db)):
    return _health_category_page(
        request=request,
        db=db,
        screen_id="health_fitness",
        screen_title="Fitness tracking",
        active_tab="fitness",
        categories=[HealthMetricCategory.FITNESS, HealthMetricCategory.RECOVERY],
        template_name="health_fitness.html",
    )


@router.get("/health/strength", response_class=HTMLResponse)
def health_strength(request: Request, db: Session = Depends(get_db)):
    return _health_category_page(
        request=request,
        db=db,
        screen_id="health_strength",
        screen_title="Strength tracking",
        active_tab="strength",
        categories=[HealthMetricCategory.STRENGTH],
        template_name="health_strength.html",
    )


@router.get("/health/flexibility", response_class=HTMLResponse)
def health_flexibility(request: Request, db: Session = Depends(get_db)):
    return _health_category_page(
        request=request,
        db=db,
        screen_id="health_flexibility",
        screen_title="Flexibility tracking",
        active_tab="flexibility",
        categories=[HealthMetricCategory.FLEXIBILITY],
        template_name="health_flexibility.html",
    )
