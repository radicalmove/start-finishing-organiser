from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, ProjectCategory
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json
from ..utils.profile import get_profile, parse_time, upsert_profile

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _parse_lines(value: str | None) -> list[str]:
    if not value:
        return []
    lines = []
    for raw in value.splitlines():
        cleaned = raw.strip().strip("-").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _seed_projects(
    db: Session,
    titles: list[str],
    category: ProjectCategory,
    active_limit: int,
) -> None:
    active_count = 0
    for title in titles:
        make_active = active_count < active_limit
        horizon = "week" if make_active else "later"
        project = Project(
            title=title,
            category=category,
            active_this_week=make_active,
            time_horizon=horizon,
            description=None,
        )
        db.add(project)
        if make_active:
            active_count += 1


@router.get("/onboarding", response_class=HTMLResponse)
def onboarding(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    profile = get_profile(db)
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="onboarding",
        screen_title="Welcome",
        screen_data={},
        db=db,
    )
    return templates.TemplateResponse(
        "onboarding.html",
        {
            "request": request,
            "profile": profile,
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/onboarding")
def submit_onboarding(
    name: str | None = Form(None),
    why_primary: str | None = Form(None),
    why_expanded: str | None = Form(None),
    values_text: str | None = Form(None),
    energy_profile: str | None = Form(None),
    workday_start: str | None = Form(None),
    workday_end: str | None = Form(None),
    weekly_review_day: str | None = Form(None),
    focus_block_preference: str | None = Form(None),
    work_projects: str | None = Form(None),
    personal_projects: str | None = Form(None),
    db: Session = Depends(get_db),
):
    profile = get_profile(db)
    payload = {
        "name": name.strip() if name else None,
        "why_primary": why_primary.strip() if why_primary else None,
        "why_expanded": why_expanded.strip() if why_expanded else None,
        "values_text": values_text.strip() if values_text else None,
        "energy_profile": energy_profile.strip() if energy_profile else None,
        "workday_start": parse_time(workday_start),
        "workday_end": parse_time(workday_end),
        "weekly_review_day": weekly_review_day.strip() if weekly_review_day else None,
        "focus_block_preference": focus_block_preference.strip() if focus_block_preference else None,
    }
    upsert_profile(db, profile, payload)

    work_list = _parse_lines(work_projects)
    personal_list = _parse_lines(personal_projects)
    if work_list:
        _seed_projects(db, work_list, ProjectCategory.WORK, 4)
    if personal_list:
        _seed_projects(db, personal_list, ProjectCategory.PERSONAL, 3)
    if work_list or personal_list:
        db.commit()

    return RedirectResponse(url="/?success=Welcome", status_code=303)
