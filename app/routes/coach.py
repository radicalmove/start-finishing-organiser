import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CoachConversation, CoachMessage
from ..security import csrf_protect, require_html_auth
from ..utils.coach import generate_coach_reply

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])


def _history_limit() -> int:
    raw = os.getenv("SFO_COACH_HISTORY_LIMIT")
    return int(raw) if raw and raw.isdigit() else 120


def _get_or_create_conversation(db: Session) -> CoachConversation:
    convo = db.query(CoachConversation).order_by(CoachConversation.created_at.desc()).first()
    if convo:
        return convo
    convo = CoachConversation()
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def _message_payload(message: CoachMessage) -> dict:
    actions = None
    if message.actions_json:
        try:
            actions = json.loads(message.actions_json)
        except json.JSONDecodeError:
            actions = None
    return {
        "role": message.role,
        "content": message.content,
        "actions": actions,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.get("/coach/history")
def coach_history(db: Session = Depends(get_db)):
    convo = _get_or_create_conversation(db)
    limit = _history_limit()
    messages = (
        db.query(CoachMessage)
        .filter(CoachMessage.conversation_id == convo.id)
        .order_by(CoachMessage.id.desc())
        .limit(limit)
        .all()
    )
    messages = list(reversed(messages))
    return JSONResponse({"messages": [_message_payload(m) for m in messages]})


@router.post("/coach/clear")
def coach_clear(db: Session = Depends(get_db)):
    convo = _get_or_create_conversation(db)
    db.delete(convo)
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/coach/message")
async def coach_message(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    context = payload.get("screen_context")
    if context is not None and not isinstance(context, dict):
        context = None

    convo = _get_or_create_conversation(db)
    history = (
        db.query(CoachMessage)
        .filter(CoachMessage.conversation_id == convo.id)
        .order_by(CoachMessage.id.asc())
        .all()
    )

    reply, actions, engine = generate_coach_reply(
        message=message,
        context=context,
        history=history,
    )

    context_json = json.dumps(context, ensure_ascii=True) if context else None
    actions_json = json.dumps(actions, ensure_ascii=True) if actions else None

    user_msg = CoachMessage(
        conversation_id=convo.id,
        role="user",
        content=message,
        context_json=context_json,
    )
    assistant_msg = CoachMessage(
        conversation_id=convo.id,
        role="assistant",
        content=reply,
        actions_json=actions_json,
    )
    convo.updated_at = datetime.utcnow()
    db.add_all([user_msg, assistant_msg, convo])
    db.commit()

    return JSONResponse({"reply": reply, "actions": actions, "engine": engine})
