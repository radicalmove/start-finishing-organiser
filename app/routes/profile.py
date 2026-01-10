from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json, project_summary
from ..utils.profile import get_profile, parse_time, upsert_profile

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    profile = get_profile(db)
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="profile",
        screen_title="Profile",
        screen_data={"projects": [project_summary(p) for p in projects]},
        db=db,
    )
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "profile": profile,
            "form_success": request.query_params.get("success"),
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/profile")
def save_profile(
    name: str | None = Form(None),
    why_primary: str | None = Form(None),
    why_expanded: str | None = Form(None),
    values_text: str | None = Form(None),
    energy_profile: str | None = Form(None),
    workday_start: str | None = Form(None),
    workday_end: str | None = Form(None),
    weekly_review_day: str | None = Form(None),
    focus_block_preference: str | None = Form(None),
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
    return RedirectResponse(url="/profile?success=Saved", status_code=303)
