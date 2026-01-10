from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import WaitingOn
from ..utils.coach import build_coach_context_json, waiting_summary
from ..security import csrf_protect, require_html_auth

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


@router.get("/waiting", response_class=HTMLResponse)
def list_waiting(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    rows = (
        db.query(WaitingOn)
        .options(selectinload(WaitingOn.project))
        .order_by(WaitingOn.created_at.desc())
        .all()
    )
    coach_context_json = build_coach_context_json(
        request_path=str(request.url.path),
        screen_id="waiting",
        screen_title="Waiting on",
        screen_data={"waiting_on": [waiting_summary(r) for r in rows]},
        db=db,
    )
    return templates.TemplateResponse(
        "waiting.html",
        {
            "request": request,
            "rows": rows,
            "form_success": request.query_params.get("success"),
            "coach_context_json": coach_context_json,
        },
    )


@router.post("/waiting/resolve")
def resolve_waiting(waiting_id: int = Form(...), db: Session = Depends(get_db)):
    row = db.get(WaitingOn, waiting_id)
    if not row:
        raise HTTPException(status_code=404, detail="Waiting item not found")
    db.delete(row)
    db.commit()
    return RedirectResponse(url="/waiting?success=Resolved", status_code=303)


@router.post("/waiting/followup")
def update_followup(
    waiting_id: int = Form(...),
    followup_date: str | None = Form(None),
    db: Session = Depends(get_db),
):
    row = db.get(WaitingOn, waiting_id)
    if not row:
        raise HTTPException(status_code=404, detail="Waiting item not found")
    parsed = None
    if followup_date:
        try:
            parsed = datetime.strptime(followup_date, "%Y-%m-%d").date()
        except ValueError:
            parsed = None
    row.last_followup = parsed
    db.add(row)
    db.commit()
    return RedirectResponse(url="/waiting?success=Follow-up saved", status_code=303)
