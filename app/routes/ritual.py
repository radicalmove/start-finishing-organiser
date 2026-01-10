from datetime import date
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Block, BlockType, Project, ProjectCategory, ProjectStatus, RitualEntry, RitualType
from ..utils.coach import build_coach_context_json, ritual_summary
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _render(
    templates,
    request,
    ritual_type: RitualType,
    last_entry: RitualEntry | None = None,
    success: str | None = None,
    coach_context_json: str | None = None,
    extra_context: dict | None = None,
):
    context = {
        "request": request,
        "ritual_type": ritual_type.value,
        "last_entry": last_entry,
        "today": date.today(),
        "form_success": success,
        "coach_context_json": coach_context_json,
    }
    if extra_context:
        context.update(extra_context)
    return templates.TemplateResponse("ritual.html", context)


def _get_last(db: Session, ritual_type: RitualType) -> RitualEntry | None:
    return (
        db.query(RitualEntry)
        .filter(RitualEntry.ritual_type == ritual_type)
        .order_by(RitualEntry.created_at.desc())
        .first()
    )


def _format_time(value) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def _summarize_blocks(blocks: list[Block]) -> list[dict]:
    items = []
    for block in blocks:
        label = block.title or block.block_type.value.title()
        if block.project:
            label = f"{label} · {block.project.title}"
        if block.start_time:
            start_label = _format_time(block.start_time)
            end_label = _format_time(block.end_time) if block.end_time else ""
            time_label = f"{start_label} - {end_label}" if end_label else start_label
        else:
            time_label = "Anytime"
        items.append({"label": label, "time": time_label})
    return items


def _summarize_events(events: list[dict]) -> list[dict]:
    items = []
    for event in events:
        if event.get("is_all_day"):
            time_label = "All day"
        else:
            start_dt = event.get("start")
            end_dt = event.get("end")
            start_label = _format_time(start_dt) if start_dt else ""
            end_label = _format_time(end_dt) if end_dt else ""
            time_label = f"{start_label} - {end_label}" if end_label else start_label
        items.append({"label": event.get("label") or "Calendar event", "time": time_label})
    return items


@router.get("/ritual/morning", response_class=HTMLResponse)
def morning(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    today = date.today()
    last_entry = _get_last(db, RitualType.MORNING)
    blocks_today = (
        db.query(Block)
        .filter(Block.date == today)
        .order_by(Block.start_time.asc().nulls_last())
        .all()
    )
    focus_blocks = [b for b in blocks_today if b.block_type == BlockType.FOCUS]
    admin_blocks = [b for b in blocks_today if b.block_type == BlockType.ADMIN]
    weekly_projects = (
        db.query(Project)
        .filter(Project.active_this_week.is_(True), Project.status == ProjectStatus.ACTIVE)
        .order_by(Project.category.asc(), Project.title.asc())
        .all()
    )
    weekly_work = [p for p in weekly_projects if p.category == ProjectCategory.WORK]
    weekly_personal = [p for p in weekly_projects if p.category == ProjectCategory.PERSONAL]
    from .homepage import _fetch_cozi_events

    cozi_events, cozi_status = _fetch_cozi_events(today)
    cozi_error = None if cozi_status.startswith("OK") else cozi_status
    last_evening = (
        db.query(RitualEntry)
        .filter(RitualEntry.ritual_type == RitualType.EVENING, RitualEntry.entry_date < today)
        .order_by(RitualEntry.entry_date.desc(), RitualEntry.created_at.desc())
        .first()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="ritual_morning",
        screen_title="Morning ritual",
        screen_data={
            "ritual_type": RitualType.MORNING.value,
            "last_entry": ritual_summary(last_entry) if last_entry else None,
        },
        db=db,
    )
    return _render(
        templates,
        request,
        RitualType.MORNING,
        last_entry,
        request.query_params.get("success"),
        coach_context_json,
        {
            "focus_blocks": _summarize_blocks(focus_blocks),
            "admin_blocks": _summarize_blocks(admin_blocks),
            "cozi_events": _summarize_events(cozi_events),
            "cozi_error": cozi_error,
            "weekly_work_projects": weekly_work,
            "weekly_personal_projects": weekly_personal,
            "last_evening": last_evening,
        },
    )


@router.get("/ritual/midday", response_class=HTMLResponse)
def midday(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    last_entry = _get_last(db, RitualType.MIDDAY)
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="ritual_midday",
        screen_title="Midday ritual",
        screen_data={
            "ritual_type": RitualType.MIDDAY.value,
            "last_entry": ritual_summary(last_entry) if last_entry else None,
        },
        db=db,
    )
    return _render(
        templates,
        request,
        RitualType.MIDDAY,
        last_entry,
        request.query_params.get("success"),
        coach_context_json,
    )


@router.get("/ritual/evening", response_class=HTMLResponse)
def evening(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    last_entry = _get_last(db, RitualType.EVENING)
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="ritual_evening",
        screen_title="Evening ritual",
        screen_data={
            "ritual_type": RitualType.EVENING.value,
            "last_entry": ritual_summary(last_entry) if last_entry else None,
        },
        db=db,
    )
    return _render(
        templates,
        request,
        RitualType.EVENING,
        last_entry,
        request.query_params.get("success"),
        coach_context_json,
    )


@router.post("/ritual/save")
def save_ritual(
    ritual_type: RitualType = Form(...),
    grounding_movement: str | None = Form(None),
    supplements_done: str | None = Form(None),
    plan_review: str | None = Form(None),
    reality_scan: str | None = Form(None),
    focus_time_status: str | None = Form(None),
    one_thing: str | None = Form(None),
    frog: str | None = Form(None),
    gratitude: str | None = Form(None),
    anticipation: str | None = Form(None),
    why_reflection: str | None = Form(None),
    why_expanded: str | None = Form(None),
    block_plan: str | None = Form(None),
    admin_plan: str | None = Form(None),
    emotional_intent: str | None = Form(None),
    wins: str | None = Form(None),
    adjustments: str | None = Form(None),
    energy: str | None = Form(None),
    notes: str | None = Form(None),
    entry_date: str | None = Form(None),
    db: Session = Depends(get_db),
):
    entry = RitualEntry(
        ritual_type=ritual_type,
        entry_date=date.fromisoformat(entry_date) if entry_date else date.today(),
        grounding_movement=grounding_movement or None,
        supplements_done=True if supplements_done else None,
        plan_review=plan_review or None,
        reality_scan=reality_scan or None,
        focus_time_status=focus_time_status or None,
        one_thing=one_thing or None,
        frog=frog or None,
        gratitude=gratitude or None,
        anticipation=anticipation or None,
        why_reflection=why_reflection or None,
        why_expanded=why_expanded or None,
        block_plan=block_plan or None,
        admin_plan=admin_plan or None,
        emotional_intent=emotional_intent or None,
        wins=wins or None,
        adjustments=adjustments or None,
        energy=energy or None,
        notes=notes or None,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse(url=f"/ritual/{ritual_type.value}?success=Saved", status_code=303)
