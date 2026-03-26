from datetime import date, datetime, timedelta

from app.models import HealthEntry
from app.models import HealthMetricCategory
from app.utils.health_views import (
    EXERCISE_DAY_OPTIONS,
    TRACKER_NAV_ITEMS,
    _json_payload,
    _latest_entries,
    _metric_stats,
    _normalize_exercise_day,
    _normalize_exercise_focus,
    _normalize_supplement_timing,
    _parse_date,
    _parse_duration_minutes,
    _parse_float,
    _parse_positive_int,
    _parse_time_value,
    _safe_int,
    _safe_redirect,
    _slugify,
)


def test_parse_and_normalize_health_inputs():
    assert _parse_date("2026-03-26") == date(2026, 3, 26)
    assert _parse_date("2026-13-26") is None

    assert _parse_float(" 42.5 ") == 42.5
    assert _parse_float(" ") is None
    assert _parse_float("abc") is None

    assert _parse_duration_minutes("45") == 45
    assert _parse_duration_minutes("0") is None
    assert _parse_duration_minutes("900") == 600

    assert _parse_positive_int("12", max_value=20) == 12
    assert _parse_positive_int("999", max_value=20) == 20
    assert _parse_positive_int("-1") is None

    assert _parse_time_value("07:30").isoformat() == "07:30:00"
    assert _parse_time_value("7:30") == datetime.strptime("07:30", "%H:%M").time()
    assert _parse_time_value("25:00") is None

    assert _safe_int("4") == 4
    assert _safe_int("null") is None
    assert _safe_int("x") is None

    assert _normalize_supplement_timing("BEDTIME") == "bedtime"
    assert _normalize_supplement_timing("weird") == "custom"
    assert _normalize_exercise_day("Friday") == "friday"
    assert _normalize_exercise_day("someday") == "monday"
    assert _normalize_exercise_focus("Strength") == "strength"
    assert _normalize_exercise_focus("balance") == "fitness"


def test_safe_redirect_and_slugify_and_tracker_nav():
    assert _safe_redirect("/health/fitness") == "/health/fitness"
    assert _safe_redirect("/tasks", fallback="/health") == "/health"
    assert _safe_redirect(None, fallback="/health/exercise") == "/health/exercise"

    assert _slugify("Blood pressure (systolic)") == "blood_pressure_systolic"
    assert _slugify("   ") == "metric"

    assert [item["key"] for item in TRACKER_NAV_ITEMS] == [
        "diet",
        "weight",
        "fitness",
        "strength",
        "flexibility",
    ]
    assert EXERCISE_DAY_OPTIONS[0] == "monday"
    assert TRACKER_NAV_ITEMS[0]["path"] == "/health/diet"
    assert HealthMetricCategory.FITNESS.value == "fitness"


def test_metric_stats_and_latest_entries_and_json_payload():
    today = date.today()
    entries = {
        1: [
            HealthEntry(metric_id=1, entry_date=today - timedelta(days=8), value=10.0),
            HealthEntry(metric_id=1, entry_date=today - timedelta(days=1), value=12.0),
            HealthEntry(metric_id=1, entry_date=today, value=15.0),
        ],
        2: [],
    }

    latest = _latest_entries(entries)
    assert latest[1].value == 15.0
    assert 2 not in latest

    stats = _metric_stats(entries)
    assert stats[1]["avg_7d"] == 13.5
    assert stats[1]["trend"] == 3.0
    assert stats[2] == {"avg_7d": None, "trend": None}

    payload = _json_payload({"tag": "</script>", "value": 3})
    assert "<\\/script>" in payload
    assert '"value": 3' in payload
