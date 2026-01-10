from __future__ import annotations

from datetime import time

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
    try:
        parts = value.split(":")
        if len(parts) < 2:
            return None
        hour = int(parts[0])
        minute = int(parts[1])
        return time(hour=hour, minute=minute)
    except (TypeError, ValueError):
        return None
