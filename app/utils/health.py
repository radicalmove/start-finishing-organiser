from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import HealthMetric, HealthMetricCategory


DEFAULT_METRICS: list[dict[str, object]] = [
    {
        "name": "Body weight",
        "slug": "body_weight",
        "category": HealthMetricCategory.WEIGHT,
        "unit": "kg",
        "description": "Scale weight.",
        "target_direction": "range",
        "is_key": True,
    },
    {
        "name": "Body fat %",
        "slug": "body_fat_percent",
        "category": HealthMetricCategory.WEIGHT,
        "unit": "%",
        "description": "Body fat percentage.",
        "target_direction": "lower",
        "is_key": False,
    },
    {
        "name": "Waist circumference",
        "slug": "waist_cm",
        "category": HealthMetricCategory.WEIGHT,
        "unit": "cm",
        "description": "Waist measurement at navel.",
        "target_direction": "lower",
        "is_key": False,
    },
    {
        "name": "Upper arm circumference",
        "slug": "upper_arm_cm",
        "category": HealthMetricCategory.WEIGHT,
        "unit": "cm",
        "description": "Relaxed upper arm measurement.",
        "target_direction": "range",
        "is_key": False,
    },
    {
        "name": "Blood pressure (systolic)",
        "slug": "bp_systolic",
        "category": HealthMetricCategory.VITALS,
        "unit": "mmHg",
        "description": "Top blood pressure number.",
        "target_direction": "lower",
        "is_key": True,
    },
    {
        "name": "Blood pressure (diastolic)",
        "slug": "bp_diastolic",
        "category": HealthMetricCategory.VITALS,
        "unit": "mmHg",
        "description": "Bottom blood pressure number.",
        "target_direction": "lower",
        "is_key": False,
    },
    {
        "name": "Resting heart rate",
        "slug": "resting_hr",
        "category": HealthMetricCategory.VITALS,
        "unit": "bpm",
        "description": "Morning resting heart rate.",
        "target_direction": "lower",
        "is_key": True,
    },
    {
        "name": "Sleep duration",
        "slug": "sleep_hours",
        "category": HealthMetricCategory.RECOVERY,
        "unit": "hours",
        "description": "Nightly sleep duration.",
        "target_direction": "range",
        "is_key": True,
    },
    {
        "name": "Calories",
        "slug": "calories",
        "category": HealthMetricCategory.DIET,
        "unit": "kcal",
        "description": "Daily calorie intake.",
        "target_direction": "range",
        "is_key": True,
    },
    {
        "name": "Protein",
        "slug": "protein_g",
        "category": HealthMetricCategory.DIET,
        "unit": "g",
        "description": "Daily protein intake.",
        "target_direction": "higher",
        "is_key": True,
    },
    {
        "name": "Fiber",
        "slug": "fiber_g",
        "category": HealthMetricCategory.DIET,
        "unit": "g",
        "description": "Daily fiber intake.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Water",
        "slug": "water_l",
        "category": HealthMetricCategory.DIET,
        "unit": "L",
        "description": "Daily water intake.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Steps",
        "slug": "steps",
        "category": HealthMetricCategory.FITNESS,
        "unit": "steps",
        "description": "Daily steps.",
        "target_direction": "higher",
        "is_key": True,
    },
    {
        "name": "Cardio minutes",
        "slug": "cardio_minutes",
        "category": HealthMetricCategory.FITNESS,
        "unit": "min",
        "description": "Moderate or vigorous cardio minutes.",
        "target_direction": "higher",
        "is_key": True,
    },
    {
        "name": "VO2 max",
        "slug": "vo2_max",
        "category": HealthMetricCategory.FITNESS,
        "unit": "ml/kg/min",
        "description": "Cardiorespiratory fitness estimate.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Strength sessions",
        "slug": "strength_sessions",
        "category": HealthMetricCategory.STRENGTH,
        "unit": "sessions",
        "description": "Strength training sessions per week.",
        "target_direction": "higher",
        "is_key": True,
    },
    {
        "name": "Squat 1RM",
        "slug": "squat_1rm",
        "category": HealthMetricCategory.STRENGTH,
        "unit": "kg",
        "description": "Estimated 1-rep max for squat.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Bench press 1RM",
        "slug": "bench_1rm",
        "category": HealthMetricCategory.STRENGTH,
        "unit": "kg",
        "description": "Estimated 1-rep max for bench press.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Deadlift 1RM",
        "slug": "deadlift_1rm",
        "category": HealthMetricCategory.STRENGTH,
        "unit": "kg",
        "description": "Estimated 1-rep max for deadlift.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Pull-ups max",
        "slug": "pullups_max",
        "category": HealthMetricCategory.STRENGTH,
        "unit": "reps",
        "description": "Max unbroken pull-ups.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Grip strength",
        "slug": "grip_strength",
        "category": HealthMetricCategory.STRENGTH,
        "unit": "kg",
        "description": "Hand-grip strength.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Mobility minutes",
        "slug": "mobility_minutes",
        "category": HealthMetricCategory.FLEXIBILITY,
        "unit": "min",
        "description": "Mobility or stretching minutes.",
        "target_direction": "higher",
        "is_key": True,
    },
    {
        "name": "Hamstring reach",
        "slug": "hamstring_reach",
        "category": HealthMetricCategory.FLEXIBILITY,
        "unit": "cm",
        "description": "Sit-and-reach distance.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Hip flexion",
        "slug": "hip_flexion",
        "category": HealthMetricCategory.FLEXIBILITY,
        "unit": "deg",
        "description": "Hip flexion range of motion.",
        "target_direction": "higher",
        "is_key": False,
    },
    {
        "name": "Shoulder flexion",
        "slug": "shoulder_flexion",
        "category": HealthMetricCategory.FLEXIBILITY,
        "unit": "deg",
        "description": "Shoulder flexion range of motion.",
        "target_direction": "higher",
        "is_key": False,
    },
]


def ensure_health_metrics(db: Session | None = None) -> None:
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True
    try:
        existing = {metric.slug for metric in db.query(HealthMetric).all()}
        new_rows: Iterable[HealthMetric] = []
        for payload in DEFAULT_METRICS:
            if payload["slug"] in existing:
                continue
            new_rows.append(HealthMetric(**payload))
        if new_rows:
            db.add_all(list(new_rows))
            db.commit()
    finally:
        if close_after:
            db.close()
