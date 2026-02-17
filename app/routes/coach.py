import json
import os
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Block,
    CoachConversation,
    CoachMessage,
    RitualEntry,
    RitualType,
    Task,
)
from ..services.coach_actions import (
    block_action_reply as _block_action_reply,
    one_thing_reply as _one_thing_reply,
    parse_one_thing_action as _parse_one_thing_action,
    parse_task_action as _parse_task_action,
    parse_time_block_action as _parse_time_block_action,
    task_action_reply as _task_action_reply,
)
from ..security import csrf_protect, require_html_auth
from ..utils.coach import generate_coach_reply, suggest_quick_actions
from ..utils.time import utc_now

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])

_STORAGE_LIST_LIMIT = 6
_STORAGE_SCREEN_LIST_LIMIT = 4
_STORAGE_MAX_BYTES = 24_000


def _trim_storage_value(value: object, limit: int) -> tuple[object, int]:
    if not isinstance(value, list):
        return value, 0
    if len(value) <= limit:
        return value, 0
    return value[:limit], len(value) - limit


def _compact_context_for_storage(context: dict | None) -> dict | None:
    if not isinstance(context, dict):
        return None

    compact: dict[str, object] = {
        "screen": context.get("screen"),
        "generated_at": context.get("generated_at"),
    }

    screen_data = context.get("screen_data")
    if isinstance(screen_data, dict):
        compact_screen: dict[str, object] = {}
        for key, value in screen_data.items():
            trimmed, extra = _trim_storage_value(value, _STORAGE_SCREEN_LIST_LIMIT)
            compact_screen[key] = trimmed
            if extra:
                compact_screen[f"{key}_more"] = extra
        compact["screen_data"] = compact_screen

    lists = context.get("lists")
    if isinstance(lists, dict):
        compact_lists: dict[str, object] = {}
        profile = lists.get("profile")
        if isinstance(profile, dict):
            compact_lists["profile"] = profile
        for key in ("projects", "tasks", "blocks", "waiting_on", "ritual_entries"):
            value = lists.get(key)
            trimmed, extra = _trim_storage_value(value, _STORAGE_LIST_LIMIT)
            if isinstance(trimmed, list):
                compact_lists[key] = trimmed
                if extra:
                    compact_lists[f"{key}_more"] = extra
        compact["lists"] = compact_lists

    payload = json.dumps(compact, ensure_ascii=True)
    if len(payload.encode("utf-8")) <= _STORAGE_MAX_BYTES:
        return compact

    fallback = {
        "screen": compact.get("screen"),
        "screen_data": compact.get("screen_data", {}),
        "generated_at": compact.get("generated_at"),
        "context_notice": "trimmed_for_storage",
    }
    return fallback


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

    effects: dict[str, object] = {}
    action = _parse_task_action(message)
    one_thing = None if action else _parse_one_thing_action(message)
    block_action = None if (action or one_thing) else _parse_time_block_action(message)
    if action:
        task = Task(
            verb_noun=action["title"],
            in_inbox=action["in_inbox"],
            when_bucket=action["when_bucket"],
        )
        db.add(task)
        db.commit()
        reply = _task_action_reply(task.verb_noun, task.in_inbox, task.when_bucket)
        actions = suggest_quick_actions(context)
        engine = "action"
        effects["refresh"] = True
        effects["type"] = "task_created"
        effects["task"] = {
            "id": task.id,
            "title": task.verb_noun,
            "in_inbox": task.in_inbox,
            "when_bucket": task.when_bucket.value if task.when_bucket else None,
        }
    elif one_thing:
        today = date.today()
        entry = (
            db.query(RitualEntry)
            .filter(RitualEntry.entry_date == today, RitualEntry.ritual_type == RitualType.MORNING)
            .order_by(RitualEntry.id.desc())
            .first()
        )
        if not entry:
            entry = RitualEntry(ritual_type=RitualType.MORNING, entry_date=today)
        entry.one_thing = one_thing
        db.add(entry)
        db.commit()
        reply = _one_thing_reply(one_thing)
        actions = suggest_quick_actions(context)
        engine = "action"
        effects["refresh"] = True
        effects["type"] = "one_thing_updated"
        effects["one_thing"] = one_thing
    elif block_action:
        block = Block(
            title=block_action["title"],
            date=block_action["date"],
            start_time=block_action["start_time"],
            end_time=block_action["end_time"],
            block_type=block_action["block_type"],
            project_id=None,
            task_id=None,
            notes=None,
        )
        db.add(block)
        db.commit()
        reply = _block_action_reply(
            block.title or "Focus block",
            block.date,
            block.start_time or time(hour=0, minute=0),
            block.end_time or time(hour=0, minute=0),
        )
        actions = suggest_quick_actions(context)
        engine = "action"
        effects["refresh"] = True
        effects["type"] = "block_created"
        effects["block"] = {
            "id": block.id,
            "title": block.title,
            "date": block.date.isoformat() if block.date else None,
            "start_time": block.start_time.isoformat() if block.start_time else None,
            "end_time": block.end_time.isoformat() if block.end_time else None,
            "block_type": block.block_type.value if block.block_type else None,
        }
    else:
        reply, actions, engine = generate_coach_reply(
            message=message,
            context=context,
            history=history,
        )

    context_for_storage = _compact_context_for_storage(context)
    context_json = json.dumps(context_for_storage, ensure_ascii=True) if context_for_storage else None
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
    convo.updated_at = utc_now()
    db.add_all([user_msg, assistant_msg, convo])
    db.commit()

    payload = {"reply": reply, "actions": actions, "engine": engine}
    if effects:
        payload["effects"] = effects
    return JSONResponse(payload)
