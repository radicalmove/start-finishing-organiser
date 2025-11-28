from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import WaitingOn

router = APIRouter()


@router.get("/waiting", response_class=HTMLResponse)
def list_waiting(request: Request, db: Session = Depends(get_db)):
    templates = request.app.state.templates
    rows = db.query(WaitingOn).order_by(WaitingOn.created_at.desc()).all()
    return templates.TemplateResponse(
        "waiting.html",
        {"request": request, "rows": rows, "form_success": request.query_params.get("success")},
    )


@router.post("/waiting/resolve")
def resolve_waiting(waiting_id: int = Form(...), db: Session = Depends(get_db)):
    row = db.get(WaitingOn, waiting_id)
    if not row:
        raise HTTPException(status_code=404, detail="Waiting item not found")
    db.delete(row)
    db.commit()
    return RedirectResponse(url="/waiting?success=Resolved", status_code=303)
