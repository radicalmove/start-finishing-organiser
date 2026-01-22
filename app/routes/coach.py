import json
import os
import re
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Block,
    BlockType,
    CoachConversation,
    CoachMessage,
    RitualEntry,
    RitualType,
    Task,
    WhenBucket,
)
from ..security import csrf_protect, require_html_auth
from ..utils.coach import generate_coach_reply, suggest_quick_actions

router = APIRouter(dependencies=[Depends(require_html_auth), Depends(csrf_protect)])

_TIME_TOKEN = r"(\\d{1,2})(?::(\\d{2}))?\\s*(am|pm)?"
_TIME_RANGE = re.compile(
    rf"(?:from\\s*)?{_TIME_TOKEN}\\s*(?:to|till|until|–|-|—)\\s*{_TIME_TOKEN}",
    re.IGNORECASE,
)


def _parse_task_action(message: str) -> dict | None:
    text = (message or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if not lowered.startswith(("add ", "create ", "capture ")):
        return None
    if "block" in lowered:
        return None
    is_capture = lowered.startswith("capture ")
    mentions_inbox = "inbox" in lowered
    mentions_task = "task" in lowered
    if not is_capture and not mentions_inbox and not mentions_task:
        return None

    title = re.sub(r"^(add|create|capture)\s+", "", text, flags=re.I).strip()
    title = re.sub(r"^(an?\s+)?(inbox|task)\s+", "", title, flags=re.I).strip()
    title = re.sub(r"\b(to|into|in)\s+inbox\b", "", title, flags=re.I).strip()

    when_bucket = None
    bucket_phrases = [
        (r"\btoday\b", WhenBucket.TODAY),
        (r"\bthis week\b", WhenBucket.WEEK),
        (r"\bnext week\b", WhenBucket.WEEK),
        (r"\bthis month\b", WhenBucket.MONTH),
        (r"\bthis quarter\b", WhenBucket.QUARTER),
        (r"\blater\b", WhenBucket.LATER),
        (r"\bsomeday\b", WhenBucket.LATER),
    ]
    if not is_capture and not mentions_inbox:
        for pattern, bucket in bucket_phrases:
            if re.search(pattern, lowered):
                when_bucket = bucket
                title = re.sub(pattern, "", title, flags=re.I).strip()
                break

    if not title:
        return None

    in_inbox = is_capture or mentions_inbox or not when_bucket
    if in_inbox:
        when_bucket = WhenBucket.LATER
    if when_bucket is None:
        when_bucket = WhenBucket.LATER

    return {
        "title": title,
        "in_inbox": in_inbox,
        "when_bucket": when_bucket,
    }


def _task_action_reply(title: str, in_inbox: bool, when_bucket: WhenBucket) -> str:
    if in_inbox:
        return (
            f"Captured in your Inbox: \"{title}\". "
            "Want to process it now or keep capturing?"
        )
    bucket_label = when_bucket.value.replace("_", " ")
    return (
        f"Added to {bucket_label.title()}: \"{title}\". "
        "Want to set a block type or duration?"
    )


def _parse_one_thing_action(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if "one thing" not in lowered:
        return None
    patterns = (
        r"(?:set|make|update)\\s+(?:my\\s+)?one thing\\s+(?:to|as)\\s+(.+)",
        r"(?:my\\s+)?one thing\\s+(?:is|=)\\s+(.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            title = match.group(1).strip().strip(".")
            if title:
                return title
    return None


def _parse_time_token(raw: str, default_ampm: str | None = None) -> time | None:
    match = re.match(r"^(\\d{1,2})(?::(\\d{2}))?\\s*(am|pm)?$", raw.strip(), re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if hour > 23 or minute > 59:
        return None
    ampm = (match.group(3) or default_ampm or "").lower()
    if ampm:
        if hour == 12:
            hour = 0 if ampm == "am" else 12
        elif ampm == "pm":
            hour += 12
    else:
        if hour == 12:
            hour = 12
        elif hour <= 7:
            hour += 12
    if hour > 23:
        return None
    return time(hour=hour, minute=minute)


def _block_type_from_text(text: str) -> BlockType:
    lowered = text.lower()
    if "admin" in lowered:
        return BlockType.ADMIN
    if "recovery" in lowered:
        return BlockType.RECOVERY
    if "social" in lowered:
        return BlockType.SOCIAL
    return BlockType.FOCUS


def _parse_time_block_action(message: str) -> dict | None:
    text = (message or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if not any(token in lowered for token in ("block", "time block", "schedule", "calendar", "book")):
        return None
    match = _TIME_RANGE.search(text)
    if not match:
        return None
    start_raw = f"{match.group(1)}{':' + match.group(2) if match.group(2) else ''}{match.group(3) or ''}"
    end_raw = f"{match.group(4)}{':' + match.group(5) if match.group(5) else ''}{match.group(6) or ''}"
    default_ampm = (match.group(3) or match.group(6) or "").lower() or None
    start_time = _parse_time_token(start_raw, default_ampm)
    end_time = _parse_time_token(end_raw, default_ampm)
    if not start_time or not end_time:
        return None
    if (end_time.hour, end_time.minute) <= (start_time.hour, start_time.minute):
        return None

    block_date = date.today()
    if "tomorrow" in lowered:
        block_date = block_date + timedelta(days=1)

    remainder = _TIME_RANGE.sub("", text).strip()
    remainder = re.sub(
        r"^(can you|please|add|create|schedule|book|block|time block|make|put)\\b",
        "",
        remainder,
        flags=re.IGNORECASE,
    ).strip()
    title = None
    for pattern in (r"\\bfor\\s+(.+)$", r"\\bto\\s+(.+)$"):
        match = re.search(pattern, remainder, flags=re.IGNORECASE)
        if match:
            title = match.group(1).strip().strip(".")
            break
    if not title:
        title = "Focus block"

    return {
        "title": title,
        "date": block_date,
        "start_time": start_time,
        "end_time": end_time,
        "block_type": _block_type_from_text(text),
    }


def _one_thing_reply(title: str) -> str:
    return (
        f"Set your One Thing to \"{title}\". "
        "It will show up on Home. Want to set a Frog too?"
    )


def _block_action_reply(title: str, block_date: date, start_time: time, end_time: time) -> str:
    date_label = block_date.strftime("%A")
    start_label = start_time.strftime("%I:%M %p").lstrip("0")
    end_label = end_time.strftime("%I:%M %p").lstrip("0")
    return (
        f"Added a block for \"{title}\" on {date_label}, {start_label}-{end_label}. "
        "Want it tied to a task?"
    )


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

    effects: dict[str, bool] = {}
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
    else:
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

    payload = {"reply": reply, "actions": actions, "engine": engine}
    if effects:
        payload["effects"] = effects
    return JSONResponse(payload)
