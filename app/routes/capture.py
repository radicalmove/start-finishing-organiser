from datetime import datetime, timedelta
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
    TaskStatus,
)
from ..utils.rules import (
    enforce_weekly_cap,
    compose_why_text,
    compute_resurface_on,
    parse_block_type,
    parse_optional_int,
)
from ..utils.coach import build_coach_context_json, project_summary, suggest_capture_kind
from ..utils.inbox_intents import (
    INBOX_INTENT_LABELS,
    INBOX_INTENT_SUPPORT_PROJECT,
    apply_inbox_container,
    mark_support_project_processed,
    normalize_inbox_intent,
    reset_to_unprocessed_inbox,
)
from ..utils.projects import normalize_project_color
from ..security import csrf_protect, require_html_auth, is_safe_redirect

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _safe_redirect(next_url: str | None, fallback: str, message: str | None = None) -> RedirectResponse:
    url = next_url if is_safe_redirect(next_url) else fallback
    if message:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}success={quote_plus(message)}"
    return RedirectResponse(url=url, status_code=303)


def _clean_title(title: str | None) -> str | None:
    if title is None:
        return None
    cleaned = title.strip()
    return cleaned or None


def _project_horizon(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"week", "month", "quarter", "year", "later"}:
        return normalized
    if normalized == "today":
        return "week"
    return "later"


def _task_when_bucket(value: str | None) -> WhenBucket:
    normalized = (value or "").strip().lower()
    mapping = {
        "today": WhenBucket.TODAY,
        "week": WhenBucket.WEEK,
        "month": WhenBucket.MONTH,
        "quarter": WhenBucket.QUARTER,
        "later": WhenBucket.LATER,
        # Tasks do not have a year bucket; year maps to later for task flow.
        "year": WhenBucket.LATER,
    }
    return mapping.get(normalized, WhenBucket.WEEK)


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
        request,
        "capture.html",
        {
            "request": request,
            "projects": projects,
            "form_error": request.query_params.get("error"),
            "form_success": request.query_params.get("success"),
            "coach_context_json": coach_context_json,
        },
    )


@router.get("/capture/process/{task_id}")
def process_inbox_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task or not task.in_inbox:
        return RedirectResponse(url="/?error=Inbox+item+not+found", status_code=303)
    from urllib.parse import quote_plus

    prefill = quote_plus(task.verb_noun.strip())
    return RedirectResponse(
        url=f"/capture/wizard?prefill={prefill}&source_task_id={task.id}",
        status_code=303,
    )


@router.get("/capture/wizard", response_class=HTMLResponse)
def capture_wizard(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    prefill = request.query_params.get("prefill") or ""
    raw_source = request.query_params.get("source_task_id")
    source_task_id = int(raw_source) if raw_source and raw_source.isdigit() else None
    source_task = db.get(Task, source_task_id) if source_task_id is not None else None
    if source_task and not source_task.in_inbox:
        source_task = None
        source_task_id = None
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="capture_wizard",
        screen_title="Guided capture",
        screen_data={"projects": [project_summary(p) for p in projects]},
        db=db,
    )
    return templates.TemplateResponse(
        request,
        "capture_wizard.html",
        {
            "request": request,
            "projects": projects,
            "guided_form_error": request.query_params.get("error"),
            "guided_modal_open": True,
            "prefill": prefill,
            "source_task_id": source_task_id,
            "prefill_details": source_task.description if source_task else "",
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/capture/wizard")
def submit_wizard(
    capture_text: str = Form(...),
    capture_description: str | None = Form(None),
    owner_type: OwnerType = Form(OwnerType.MINE),
    item_kind: str = Form("task"),
    inbox_intent: str | None = Form(None),
    displacement_ack: str | None = Form(None),
    source_task_id: int | None = Form(None),
    next_url: str | None = Form(None),
    category: ProjectCategory = Form(ProjectCategory.WORK),
    project_id: str | None = Form(""),
    project_color_scheme: str | None = Form(None),
    horizon: str = Form("week"),
    include_this_week: str = Form("yes"),
    why_link_text: str | None = Form(None),
    why_tags: list[str] | None = Form(None),
    block_type: str | None = Form(""),
    duration_minutes: str | None = Form(None),
    frog: bool = Form(False),
    waiting_person: str | None = Form(None),
    db: Session = Depends(get_db),
):
    cleaned_title = _clean_title(capture_text)
    if not cleaned_title:
        msg = quote_plus("Title is required.")
        source = f"&source_task_id={source_task_id}" if source_task_id else ""
        return RedirectResponse(
            url=f"/capture/wizard?error={msg}{source}",
            status_code=303,
        )
    task_horizon = _task_when_bucket(horizon)
    project_horizon = _project_horizon(horizon)
    active_this_week = include_this_week.lower() == "yes" or project_horizon == "week"
    pid = int(project_id) if project_id not in (None, "", "null") else None
    btype = parse_block_type(block_type) if block_type not in (None, "", "null") else None
    duration_value = parse_optional_int(duration_minutes)
    if duration_value is not None and duration_value <= 0:
        duration_value = None
    details = capture_description.strip() if capture_description else None
    source_task = db.get(Task, source_task_id) if source_task_id else None
    if source_task and not source_task.in_inbox:
        source_task = None
    if details is None and source_task:
        details = source_task.description

    normalized_intent = normalize_inbox_intent(inbox_intent)
    if source_task and normalized_intent is None:
        msg = quote_plus("Choose how to handle this inbox item before saving.")
        prefill = quote_plus(cleaned_title)
        source = f"&source_task_id={source_task_id}" if source_task_id else ""
        return RedirectResponse(
            url=f"/capture/wizard?error={msg}&prefill={prefill}{source}",
            status_code=303,
        )
    if normalized_intent is None:
        normalized_intent = INBOX_INTENT_SUPPORT_PROJECT

    if (
        normalized_intent == INBOX_INTENT_SUPPORT_PROJECT
        and item_kind in {"task", "project"}
        and (displacement_ack or "").lower() not in {"1", "true", "yes"}
    ):
        msg = quote_plus("Confirm the displacement check before saving.")
        prefill = quote_plus(cleaned_title)
        source = f"&source_task_id={source_task_id}" if source_task_id else ""
        return RedirectResponse(
            url=f"/capture/wizard?error={msg}&prefill={prefill}{source}",
            status_code=303,
        )
    if (
        source_task
        and normalized_intent == INBOX_INTENT_SUPPORT_PROJECT
        and item_kind == "task"
        and pid is None
    ):
        msg = quote_plus("Select an existing project or choose Project flow.")
        prefill = quote_plus(cleaned_title)
        source = f"&source_task_id={source_task_id}" if source_task_id else ""
        return RedirectResponse(
            url=f"/capture/wizard?error={msg}&prefill={prefill}{source}",
            status_code=303,
        )

    try:
        if source_task and normalized_intent != INBOX_INTENT_SUPPORT_PROJECT:
            source_task.verb_noun = cleaned_title
            source_task.description = details
            apply_inbox_container(source_task, normalized_intent)
            db.add(source_task)
            db.commit()
            message = f"Saved to {INBOX_INTENT_LABELS.get(normalized_intent, 'container')}"
            return _safe_redirect(next_url, "/", message)

        if item_kind == "decide_later":
            details = capture_description.strip() if capture_description else None
            if source_task:
                source_task.verb_noun = cleaned_title
                source_task.description = details
                reset_to_unprocessed_inbox(source_task)
            else:
                task = Task(
                    verb_noun=cleaned_title,
                    project_id=None,
                    description=details,
                    in_inbox=True,
                    when_bucket=WhenBucket.LATER,
                    block_type=None,
                    duration_minutes=None,
                    frog=False,
                    owner_type=owner_type,
                )
                db.add(task)
            db.commit()
            return _safe_redirect(next_url, "/", "Captured")
        if item_kind == "project":
            if active_this_week:
                enforce_weekly_cap(db, category, True)
            project = Project(
                title=cleaned_title,
                category=category,
                active_this_week=active_this_week,
                time_horizon=project_horizon,
                why_link_text=compose_why_text(why_link_text, why_tags),
                color_scheme=normalize_project_color(project_color_scheme),
                description=details,
            )
            db.add(project)
            if source_task:
                mark_support_project_processed(source_task)
                source_task.in_inbox = False
                source_task.archived_from_inbox = True
                source_task.status = TaskStatus.ARCHIVED
        else:
            if source_task:
                task = source_task
                task.verb_noun = cleaned_title
                task.project_id = pid
                task.description = details
                task.in_inbox = False
                task.archived_from_inbox = False
                task.when_bucket = task_horizon
                task.block_type = btype
                task.duration_minutes = duration_value
                task.frog = frog
                task.owner_type = owner_type
                task.alignment = None
                task.resurface_on = compute_resurface_on(task_horizon.value)
                task.status = TaskStatus.PENDING
                task.completed_at = None
                mark_support_project_processed(task)
            else:
                task = Task(
                    verb_noun=cleaned_title,
                    project_id=pid,
                    description=details,
                    in_inbox=False,
                    when_bucket=task_horizon,
                    block_type=btype,
                    duration_minutes=duration_value,
                    frog=frog,
                    owner_type=owner_type,
                    alignment=None,
                    resurface_on=compute_resurface_on(task_horizon.value),
                )
                db.add(task)
            if owner_type == OwnerType.OPP:
                person = waiting_person.strip() if waiting_person else None
                waiting_exists = (
                    db.query(WaitingOn)
                    .filter(
                        WaitingOn.description == cleaned_title,
                        WaitingOn.project_id == pid,
                        WaitingOn.person == person,
                    )
                    .first()
                    is not None
                )
                if not waiting_exists:
                    waiting = WaitingOn(
                        description=cleaned_title,
                        person=person,
                        project_id=pid,
                    )
                    db.add(waiting)
        db.commit()
    except HTTPException as exc:
        msg = compose_cap_error(exc)
        prefill = quote_plus(cleaned_title)
        source = f"&source_task_id={source_task_id}" if source_task_id else ""
        return RedirectResponse(
            url=f"/capture/wizard?error={msg}&prefill={prefill}{source}",
            status_code=303,
        )

    return _safe_redirect(next_url, "/", "Captured")


@router.post("/capture/wizard/suggest")
async def suggest_wizard_kind(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    details = (payload.get("details") or "").strip()
    if not details:
        raise HTTPException(status_code=400, detail="Add more detail for a suggestion.")
    size = payload.get("size") or None
    next_action = payload.get("next_action") or None
    title = payload.get("title") or None
    kind, rationale, engine = suggest_capture_kind(
        details=details,
        size=size,
        next_action=next_action,
        title=title,
    )
    if kind not in {"task", "project"}:
        kind = "task"
    return JSONResponse({"kind": kind, "rationale": rationale, "engine": engine})


@router.post("/capture")
def submit_capture(
    title: str = Form(...),
    capture_kind: str = Form("decide_later"),
    displacement_ack: str | None = Form(None),
    next_url: str | None = Form(None),
    task_project_id: str | None = Form(""),
    task_description: str | None = Form(None),
    task_when_bucket: WhenBucket = Form(WhenBucket.TODAY),
    task_block_type: str | None = Form(""),
    task_duration_minutes: str | None = Form(None),
    task_frog: bool = Form(False),
    project_category: ProjectCategory = Form(ProjectCategory.WORK),
    project_time_horizon: str = Form("week"),
    project_include_this_week: str = Form("yes"),
    project_description: str | None = Form(None),
    project_why_link_text: str | None = Form(None),
    project_why_tags: list[str] | None = Form(None),
    project_color_scheme: str | None = Form(None),
    block_project_id: str | None = Form(""),
    block_date: str | None = Form(None),
    block_start_time: str | None = Form(None),
    block_duration_minutes: str | None = Form(None),
    block_type: str | None = Form(""),
    block_notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    cleaned_title = _clean_title(title) or ""
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
                in_inbox=True,
                when_bucket=WhenBucket.LATER,
                block_type=None,
                duration_minutes=None,
                frog=False,
            )
            db.add(task)
            db.commit()
            return _safe_redirect(next_url, "/", "Captured")

        if capture_kind == "task":
            pid = int(task_project_id) if task_project_id not in (None, "", "null") else None
            btype = task_block_type if task_block_type not in (None, "", "null") else None
            duration_value = parse_optional_int(task_duration_minutes)
            if duration_value is not None and duration_value <= 0:
                duration_value = None
            task = Task(
                verb_noun=cleaned_title,
                project_id=pid,
                description=task_description or None,
                in_inbox=False,
                when_bucket=task_when_bucket,
                block_type=parse_block_type(btype),
                duration_minutes=duration_value,
                frog=task_frog,
                resurface_on=compute_resurface_on(
                    task_when_bucket.value
                    if hasattr(task_when_bucket, "value")
                    else str(task_when_bucket)
                ),
            )
            db.add(task)
            db.commit()
            return _safe_redirect(next_url, "/", "Captured")

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
                time_horizon=_project_horizon(project_time_horizon),
                why_link_text=compose_why_text(project_why_link_text, project_why_tags),
                color_scheme=normalize_project_color(project_color_scheme),
                description=project_description or None,
            )
            db.add(project)
            db.commit()
            return _safe_redirect(next_url, "/", "Captured")

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

            block_minutes = parse_optional_int(block_duration_minutes)
            if block_minutes is None or block_minutes <= 0:
                raise HTTPException(status_code=400, detail="Duration is required.")
            dur = max(5, block_minutes)

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
