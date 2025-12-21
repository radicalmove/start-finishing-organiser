from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Project,
    Task,
    ProjectCategory,
    WhenBucket,
    OwnerType,
    WaitingOn,
)
from ..utils.rules import enforce_weekly_cap, compose_why_text, compute_resurface_on, parse_block_type
from ..utils.coach import build_coach_context_json, project_summary
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


@router.get("/capture", response_class=HTMLResponse)
def capture(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="capture",
        screen_title="Quick capture",
        screen_data={"projects": [project_summary(p) for p in projects]},
        db=db,
    )

    return templates.TemplateResponse(
        "capture.html",
        {
            "request": request,
            "projects": projects,
            "form_error": request.query_params.get("error"),
            "form_success": request.query_params.get("success"),
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/capture/wizard", response_class=HTMLResponse)
def capture_wizard(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="capture_wizard",
        screen_title="Guided capture",
        screen_data={"projects": [project_summary(p) for p in projects]},
        db=db,
    )
    return templates.TemplateResponse(
        "capture_wizard.html",
        {
            "request": request,
            "projects": projects,
            "form_error": request.query_params.get("error"),
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/capture/wizard")
def submit_wizard(
    capture_text: str = Form(...),
    owner_type: OwnerType = Form(OwnerType.MINE),
    item_kind: str = Form("task"),
    category: ProjectCategory = Form(ProjectCategory.WORK),
    project_id: str | None = Form(""),
    horizon: WhenBucket = Form(WhenBucket.WEEK),
    include_this_week: str = Form("yes"),
    why_link_text: str | None = Form(None),
    why_tags: list[str] | None = Form(None),
    block_type: str | None = Form(""),
    duration_minutes: int | None = Form(None),
    frog: bool = Form(False),
    waiting_person: str | None = Form(None),
    db: Session = Depends(get_db),
):
    active_this_week = include_this_week.lower() == "yes" or horizon == WhenBucket.WEEK
    pid = int(project_id) if project_id not in (None, "", "null") else None
    btype = parse_block_type(block_type) if block_type not in (None, "", "null") else None

    try:
        if item_kind == "project":
            if active_this_week:
                enforce_weekly_cap(db, category, True)
            project = Project(
                title=capture_text.strip(),
                category=category,
                active_this_week=active_this_week,
                time_horizon=horizon.value if isinstance(horizon, WhenBucket) else horizon,
                why_link_text=compose_why_text(why_link_text, why_tags),
                description=None,
            )
            db.add(project)
        else:
            task = Task(
                verb_noun=capture_text.strip(),
                project_id=pid,
                description=None,
                when_bucket=horizon,
                block_type=btype,
                duration_minutes=duration_minutes or None,
                frog=frog,
                owner_type=owner_type,
                alignment=None,
                resurface_on=compute_resurface_on(horizon.value if hasattr(horizon, "value") else str(horizon)),
            )
            db.add(task)
            if owner_type == OwnerType.OPP:
                waiting = WaitingOn(
                    description=capture_text.strip(),
                    person=waiting_person or None,
                    project_id=pid,
                )
                db.add(waiting)
        db.commit()
    except HTTPException as exc:
        msg = compose_cap_error(exc)
        return RedirectResponse(url=f"/capture/wizard?error={msg}", status_code=303)

    return RedirectResponse(url="/?success=Captured", status_code=303)


def compose_cap_error(exc: HTTPException) -> str:
    from urllib.parse import quote_plus

    return quote_plus(str(exc.detail))
