from datetime import date
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import RitualEntry, RitualType

router = APIRouter()


def _render(templates, request, ritual_type: RitualType, last_entry: RitualEntry | None = None, success: str | None = None):
    return templates.TemplateResponse(
        "ritual.html",
        {
            "request": request,
            "ritual_type": ritual_type.value,
            "last_entry": last_entry,
            "form_success": success,
        },
    )


def _get_last(db: Session, ritual_type: RitualType) -> RitualEntry | None:
    return (
        db.query(RitualEntry)
        .filter(RitualEntry.ritual_type == ritual_type)
        .order_by(RitualEntry.created_at.desc())
        .first()
    )


@router.get("/ritual/morning", response_class=HTMLResponse)
def morning(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    return _render(templates, request, RitualType.MORNING, _get_last(db, RitualType.MORNING), request.query_params.get("success"))


@router.get("/ritual/midday", response_class=HTMLResponse)
def midday(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    return _render(templates, request, RitualType.MIDDAY, _get_last(db, RitualType.MIDDAY), request.query_params.get("success"))


@router.get("/ritual/evening", response_class=HTMLResponse)
def evening(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    return _render(templates, request, RitualType.EVENING, _get_last(db, RitualType.EVENING), request.query_params.get("success"))


@router.post("/ritual/save")
def save_ritual(
    ritual_type: RitualType = Form(...),
    one_thing: str | None = Form(None),
    frog: str | None = Form(None),
    gratitude: str | None = Form(None),
    why_reflection: str | None = Form(None),
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
        one_thing=one_thing or None,
        frog=frog or None,
        gratitude=gratitude or None,
        why_reflection=why_reflection or None,
        wins=wins or None,
        adjustments=adjustments or None,
        energy=energy or None,
        notes=notes or None,
    )
    db.add(entry)
    db.commit()
    return RedirectResponse(url=f"/ritual/{ritual_type.value}?success=Saved", status_code=303)
