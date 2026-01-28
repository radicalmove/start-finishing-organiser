from __future__ import annotations

from datetime import time
import re

from sqlalchemy.orm import Session

from ..models import Profile


def get_profile(db: Session) -> Profile | None:
    return db.query(Profile).order_by(Profile.id.asc()).first()


def upsert_profile(db: Session, profile: Profile | None, payload: dict) -> Profile:
    if profile is None:
        profile = Profile(**payload)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    for key, value in payload.items():
        setattr(profile, key, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def parse_time(value: str | None) -> time | None:
    if not value:
        return None
    cleaned = value.strip().lower().replace(".", ":")
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", cleaned)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return time(hour=hour, minute=minute)
    match = re.match(r"^(\d{1,2}):(\d{2})$", cleaned)
    if match:
        try:
            hour = int(match.group(1))
            minute = int(match.group(2))
            return time(hour=hour, minute=minute)
        except (TypeError, ValueError):
            return None
    return None
