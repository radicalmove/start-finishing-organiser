from urllib.parse import quote_plus
from fastapi import HTTPException
from datetime import date, timedelta

from ..models import Project, ProjectCategory
from sqlalchemy.orm import Session


def enforce_weekly_cap(db: Session, category: ProjectCategory, make_active: bool) -> None:
    """Prevent adding more than 4 work or 3 personal active projects per week."""
    if not make_active:
        return
    cap = 4 if category == ProjectCategory.WORK else 3
    current = (
        db.query(Project)
        .filter(Project.category == category, Project.active_this_week.is_(True))
        .count()
    )
    if current >= cap:
        raise HTTPException(
            status_code=400,
            detail=f"Weekly cap reached for {category.value} projects ({current}/{cap}).",
        )


def compose_why_text(free_text: str | None, tags: list[str] | None) -> str | None:
    """Combine quick Why tags with free text into one stored field."""
    tag_part = ""
    if tags:
        tag_part = "Tags: " + ", ".join([t for t in tags if t.strip()])
    parts = [p for p in [free_text or None, tag_part or None] if p]
    return "\n".join(parts) if parts else None


def cap_error_redirect(exc: HTTPException) -> str:
    """Return redirect query string for cap errors."""
    return quote_plus(str(exc.detail))


def compute_resurface_on(horizon: str) -> date | None:
    """Return a suggested resurface date based on horizon."""
    today = date.today()
    if horizon in ("today", "week"):
        return None
    if horizon == "month":
        return today + timedelta(days=7)
    if horizon == "quarter":
        return today + timedelta(days=14)
    return today + timedelta(days=30)
