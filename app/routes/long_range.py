from datetime import datetime, date

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Project, ProjectStatus, ProjectCategory, ProjectSize, SuccessLevel, SuccessPack
from ..security import csrf_protect, require_html_auth
from ..utils.coach import build_coach_context_json, project_summary
from ..utils.rules import enforce_weekly_cap

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _normalize_horizon(value: str | None) -> str:
    if not value:
        return "unspecified"
    lowered = value.strip().lower()
    if lowered in {"year", "annual", "long", "long range", "long-term", "long term"}:
        return "year"
    if lowered in {"quarter", "quarterly", "qtr"}:
        return "quarter"
    if lowered in {"month", "monthly"}:
        return "month"
    if lowered in {"week", "weekly"}:
        return "week"
    if lowered in {"later", "someday", "someday/maybe", "someday maybe"}:
        return "later"
    return "unspecified"


def _parse_optional_enum(value: str | None, enum_cls):
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def _parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_horizon_input(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    if cleaned in {"unspecified", "unsorted", "none", "null"}:
        return None
    return cleaned or None


def _build_long_range_context(
    request: Request,
    db: Session,
    screen_id: str,
    screen_title: str,
    active_tab: str,
) -> dict:
    projects = (
        db.query(Project)
        .options(selectinload(Project.success_pack))
        .filter(Project.status != ProjectStatus.ARCHIVED)
        .order_by(Project.created_at.desc())
        .all()
    )

    horizons: dict[str, list[Project]] = {
        "year": [],
        "quarter": [],
        "month": [],
        "week": [],
        "later": [],
        "unspecified": [],
    }
    for project in projects:
        horizon_key = _normalize_horizon(project.time_horizon)
        horizons[horizon_key].append(project)

    horizon_columns = [
        {"key": "week", "label": "Week", "hint": "Active focus", "empty": "No weekly projects yet."},
        {"key": "month", "label": "Month", "hint": "4-week focus", "empty": "No monthly projects yet."},
        {"key": "quarter", "label": "Quarter", "hint": "90-day bets", "empty": "No quarterly projects yet."},
        {"key": "year", "label": "Year +", "hint": "3-5 year arcs", "empty": "No year projects yet."},
        {"key": "later", "label": "Later", "hint": "Someday or maybe", "empty": "Nothing parked for later."},
        {"key": "unspecified", "label": "Unsorted", "hint": "Set a horizon", "empty": "All projects have a horizon."},
    ]

    roadmap_projects = [
        project
        for project in projects
        if _normalize_horizon(project.time_horizon) in {"year", "quarter"}
    ]
    roadmap_projects = sorted(
        roadmap_projects, key=lambda project: (project.target_date or project.created_at)
    )

    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id=screen_id,
        screen_title=screen_title,
        screen_data={
            "horizon_counts": {key: len(values) for key, values in horizons.items()},
            "roadmap_projects": [project_summary(project) for project in roadmap_projects],
        },
        db=db,
    )

    return {
        "request": request,
        "projects": projects,
        "horizons": horizons,
        "horizon_columns": horizon_columns,
        "roadmap_projects": roadmap_projects,
        "coach_context_json": coach_context_json,
        "active_long_term_tab": active_tab,
    }


@router.post("/long-term/projects/{project_id}/update")
def update_long_range_project(
    project_id: int,
    title: str | None = Form(None),
    description: str | None = Form(None),
    category: str | None = Form(None),
    time_horizon: str | None = Form(None),
    target_date: str | None = Form(None),
    size: str | None = Form(None),
    level_of_success: str | None = Form(None),
    why_link_text: str | None = Form(None),
    drag_points_notes: str | None = Form(None),
    success_pack_guides: str | None = Form(None),
    success_pack_peers: str | None = Form(None),
    success_pack_supporters: str | None = Form(None),
    success_pack_beneficiaries: str | None = Form(None),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if title is not None:
        cleaned = title.strip()
        if cleaned:
            project.title = cleaned

    if description is not None:
        project.description = description.strip() or None

    if time_horizon is not None:
        project.time_horizon = time_horizon.strip().lower() or None

    parsed_category = _parse_optional_enum(category, ProjectCategory)
    if parsed_category:
        project.category = parsed_category

    parsed_size = _parse_optional_enum(size, ProjectSize)
    if parsed_size or size == "":
        project.size = parsed_size

    parsed_level = _parse_optional_enum(level_of_success, SuccessLevel)
    if parsed_level or level_of_success == "":
        project.level_of_success = parsed_level

    if target_date is not None:
        project.target_date = _parse_optional_date(target_date)

    if why_link_text is not None:
        project.why_link_text = why_link_text.strip() or None

    if drag_points_notes is not None:
        project.drag_points_notes = drag_points_notes.strip() or None

    if any(
        value is not None
        for value in (
            success_pack_guides,
            success_pack_peers,
            success_pack_supporters,
            success_pack_beneficiaries,
        )
    ):
        if project.success_pack is None:
            project.success_pack = SuccessPack(project_id=project.id)
        project.success_pack.guides = success_pack_guides.strip() if success_pack_guides else None
        project.success_pack.peers = success_pack_peers.strip() if success_pack_peers else None
        project.success_pack.supporters = (
            success_pack_supporters.strip() if success_pack_supporters else None
        )
        project.success_pack.beneficiaries = (
            success_pack_beneficiaries.strip() if success_pack_beneficiaries else None
        )

    db.add(project)
    db.commit()
    return RedirectResponse(url="/long-term", status_code=303)


@router.post("/long-term/projects/{project_id}/horizon", response_class=JSONResponse)
def update_long_range_horizon(
    project_id: int,
    time_horizon: str | None = Form(None),
    db: Session = Depends(get_db),
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    normalized = _normalize_horizon_input(time_horizon)
    make_active = normalized == "week"
    if make_active and not project.active_this_week:
        enforce_weekly_cap(db, project.category, True)

    project.time_horizon = normalized
    if normalized == "week":
        project.active_this_week = True
    else:
        project.active_this_week = False

    db.add(project)
    db.commit()
    return {"ok": True, "time_horizon": normalized or "unspecified"}


@router.get("/long-range")
def long_range_redirect():
    return RedirectResponse(url="/long-term", status_code=307)


@router.get("/long-term", response_class=HTMLResponse)
def long_range_horizons(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    context = _build_long_range_context(
        request=request,
        db=db,
        screen_id="long_range_horizons",
        screen_title="Long term planning — Horizon map",
        active_tab="horizons",
    )
    return templates.TemplateResponse(
        "long_range.html",
        context,
    )


@router.get("/long-term/pyramid", response_class=HTMLResponse)
def long_range_pyramid(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    context = _build_long_range_context(
        request=request,
        db=db,
        screen_id="long_range_pyramid",
        screen_title="Long term planning — Project pyramid",
        active_tab="pyramid",
    )
    return templates.TemplateResponse(
        "long_range_pyramid.html",
        context,
    )


@router.get("/long-term/roadmaps", response_class=HTMLResponse)
def long_range_roadmaps(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    context = _build_long_range_context(
        request=request,
        db=db,
        screen_id="long_range_roadmaps",
        screen_title="Long term planning — Project roadmaps",
        active_tab="roadmaps",
    )
    return templates.TemplateResponse(
        "long_range_roadmaps.html",
        context,
    )
