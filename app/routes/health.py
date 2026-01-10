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
    HealthGoal,
    HealthMetric,
    HealthMetricCategory,
)
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


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
        "health_dashboard.html",
        {
            "request": request,
            "active_health_tab": "dashboard",
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
        template_name,
        {
            "request": request,
            "active_health_tab": active_tab,
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
