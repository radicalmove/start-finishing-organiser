from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import re
from typing import Iterable

from sqlalchemy.orm import Session

from ..models import HealthEntry, HealthMetric, HealthMetricCategory

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
