from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Block,
    Project,
    Task,
    ProjectCategory,
    WhenBucket,
    OwnerType,
    WaitingOn,
)
from ..utils.rules import (
    enforce_weekly_cap,
    compose_why_text,
    compute_resurface_on,
    parse_block_type,
)
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
    prefill = request.query_params.get("prefill") or ""
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
            "prefill": prefill,
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/capture/wizard")
def submit_wizard(
    capture_text: str = Form(...),
    owner_type: OwnerType = Form(OwnerType.MINE),
    item_kind: str = Form("task"),
    displacement_ack: str | None = Form(None),
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
    if item_kind in {"task", "project"} and (displacement_ack or "").lower() not in {"1", "true", "yes"}:
        from urllib.parse import quote_plus

        msg = quote_plus("Confirm the displacement check before saving.")
        prefill = quote_plus(capture_text.strip())
        return RedirectResponse(url=f"/capture/wizard?error={msg}&prefill={prefill}", status_code=303)
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


@router.post("/capture")
def submit_capture(
    title: str = Form(...),
    capture_kind: str = Form("decide_later"),
    displacement_ack: str | None = Form(None),
    task_project_id: str | None = Form(""),
    task_description: str | None = Form(None),
    task_when_bucket: WhenBucket = Form(WhenBucket.TODAY),
    task_block_type: str | None = Form(""),
    task_duration_minutes: int | None = Form(None),
    task_frog: bool = Form(False),
    project_category: ProjectCategory = Form(ProjectCategory.WORK),
    project_time_horizon: str = Form("week"),
    project_include_this_week: str = Form("yes"),
    project_description: str | None = Form(None),
    project_why_link_text: str | None = Form(None),
    project_why_tags: list[str] | None = Form(None),
    block_project_id: str | None = Form(""),
    block_date: str | None = Form(None),
    block_start_time: str | None = Form(None),
    block_duration_minutes: int | None = Form(None),
    block_type: str | None = Form(""),
    block_notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    cleaned_title = title.strip()
    if not cleaned_title:
        return RedirectResponse(url="/capture?error=Title+is+required", status_code=303)

    if capture_kind in {"task", "project"} and (displacement_ack or "").lower() not in {"1", "true", "yes"}:
        return RedirectResponse(
            url="/capture?error=Confirm+the+displacement+check+before+saving.",
            status_code=303,
        )

    if capture_kind == "not_sure":
        from urllib.parse import quote_plus

        return RedirectResponse(
            url=f"/capture/wizard?prefill={quote_plus(cleaned_title)}",
            status_code=303,
        )

    try:
        if capture_kind == "decide_later":
            task = Task(
                verb_noun=cleaned_title,
                project_id=None,
                description=None,
                when_bucket=WhenBucket.LATER,
                block_type=None,
                duration_minutes=None,
                frog=False,
            )
            db.add(task)
            db.commit()
            return RedirectResponse(url="/?success=Captured", status_code=303)

        if capture_kind == "task":
            pid = int(task_project_id) if task_project_id not in (None, "", "null") else None
            btype = task_block_type if task_block_type not in (None, "", "null") else None
            task = Task(
                verb_noun=cleaned_title,
                project_id=pid,
                description=task_description or None,
                when_bucket=task_when_bucket,
                block_type=parse_block_type(btype),
                duration_minutes=task_duration_minutes or None,
                frog=task_frog,
            )
            db.add(task)
            db.commit()
            return RedirectResponse(url="/?success=Captured", status_code=303)

        if capture_kind == "project":
            active_this_week = (
                project_include_this_week.lower() == "yes" or project_time_horizon == "week"
            )
            if active_this_week:
                enforce_weekly_cap(db, project_category, True)

            project = Project(
                title=cleaned_title,
                category=project_category,
                active_this_week=active_this_week,
                time_horizon=project_time_horizon,
                why_link_text=compose_why_text(project_why_link_text, project_why_tags),
                description=project_description or None,
            )
            db.add(project)
            db.commit()
            return RedirectResponse(url="/?success=Captured", status_code=303)

        if capture_kind == "time_block":
            if not block_date or not block_start_time:
                raise HTTPException(status_code=400, detail="Date and time are required.")
            try:
                date_val = datetime.strptime(block_date, "%Y-%m-%d").date()
                start_val = datetime.strptime(block_start_time, "%H:%M").time()
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid date or time") from exc

            parsed_block_type = parse_block_type(block_type)
            if parsed_block_type is None:
                raise HTTPException(status_code=400, detail="Block type is required.")

            if block_duration_minutes is None or block_duration_minutes <= 0:
                raise HTTPException(status_code=400, detail="Duration is required.")
            dur = max(5, block_duration_minutes)

            start_dt = datetime.combine(date_val, start_val)
            end_dt = start_dt + timedelta(minutes=dur)
            if end_dt.date() != date_val:
                raise HTTPException(status_code=400, detail="Blocks cannot span midnight.")
            end_val = end_dt.time()

            pid = int(block_project_id) if block_project_id not in (None, "", "null") else None
            block = Block(
                title=cleaned_title,
                date=date_val,
                start_time=start_val,
                end_time=end_val,
                block_type=parsed_block_type,
                project_id=pid,
                task_id=None,
                notes=block_notes.strip() if block_notes else None,
            )
            db.add(block)
            db.commit()
            return RedirectResponse(url="/?success=Captured", status_code=303)

        raise HTTPException(status_code=400, detail="Select a capture type.")
    except HTTPException as exc:
        msg = compose_cap_error(exc)
        return RedirectResponse(url=f"/capture?error={msg}", status_code=303)


def compose_cap_error(exc: HTTPException) -> str:
    from urllib.parse import quote_plus

    return quote_plus(str(exc.detail))
