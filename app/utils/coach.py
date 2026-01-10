from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, time
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy.orm import Session, selectinload

from ..models import Block, CoachMessage, Project, RitualEntry, Task, WaitingOn

_DEFAULT_QUOTE_CHANCE = 0.12
_DEFAULT_HISTORY_LIMIT = 120
_DEFAULT_LLM_TIMEOUT = 15


def _to_iso(value: date | datetime | time | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value)


def project_summary(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "title": project.title,
        "category": project.category.value if project.category else None,
        "status": project.status.value if project.status else None,
        "size": project.size.value if project.size else None,
        "time_horizon": project.time_horizon,
        "start_date": _to_iso(project.start_date),
        "target_date": _to_iso(project.target_date),
        "level_of_success": project.level_of_success.value if project.level_of_success else None,
        "why_link_text": project.why_link_text,
        "active_this_week": project.active_this_week,
        "created_at": _to_iso(project.created_at),
    }


def task_summary(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "verb_noun": task.verb_noun,
        "description": task.description,
        "project_id": task.project_id,
        "project_title": task.project.title if task.project else None,
        "when_bucket": task.when_bucket.value if task.when_bucket else None,
        "block_type": task.block_type.value if task.block_type else None,
        "duration_minutes": task.duration_minutes,
        "priority": task.priority,
        "frog": task.frog,
        "alignment": task.alignment.value if task.alignment else None,
        "first_action": task.first_action,
        "status": task.status.value if task.status else None,
        "scheduled_for": _to_iso(task.scheduled_for),
        "owner_type": task.owner_type.value if task.owner_type else None,
        "resurface_on": _to_iso(task.resurface_on),
        "created_at": _to_iso(task.created_at),
    }


def block_summary(block: Block) -> dict[str, Any]:
    return {
        "id": block.id,
        "title": block.title,
        "date": _to_iso(block.date),
        "start_time": _to_iso(block.start_time),
        "end_time": _to_iso(block.end_time),
        "block_type": block.block_type.value if block.block_type else None,
        "project_id": block.project_id,
        "project_title": block.project.title if block.project else None,
        "task_id": block.task_id,
        "notes": block.notes,
        "created_at": _to_iso(block.created_at),
    }


def waiting_summary(waiting: WaitingOn) -> dict[str, Any]:
    return {
        "id": waiting.id,
        "description": waiting.description,
        "person": waiting.person,
        "project_id": waiting.project_id,
        "project_title": waiting.project.title if waiting.project else None,
        "created_at": _to_iso(waiting.created_at),
        "last_followup": _to_iso(waiting.last_followup),
    }


def ritual_summary(entry: RitualEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "ritual_type": entry.ritual_type.value if entry.ritual_type else None,
        "entry_date": _to_iso(entry.entry_date),
        "grounding_movement": entry.grounding_movement,
        "supplements_done": entry.supplements_done,
        "plan_review": entry.plan_review,
        "reality_scan": entry.reality_scan,
        "focus_time_status": entry.focus_time_status,
        "one_thing": entry.one_thing,
        "frog": entry.frog,
        "gratitude": entry.gratitude,
        "anticipation": entry.anticipation,
        "why_reflection": entry.why_reflection,
        "why_expanded": entry.why_expanded,
        "block_plan": entry.block_plan,
        "admin_plan": entry.admin_plan,
        "emotional_intent": entry.emotional_intent,
        "wins": entry.wins,
        "adjustments": entry.adjustments,
        "energy": entry.energy,
        "notes": entry.notes,
        "created_at": _to_iso(entry.created_at),
    }


def collect_global_context(db: Session) -> dict[str, Any]:
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    tasks = (
        db.query(Task)
        .options(selectinload(Task.project))
        .order_by(Task.created_at.desc())
        .all()
    )
    blocks = (
        db.query(Block)
        .options(selectinload(Block.project))
        .order_by(Block.date.desc(), Block.start_time.desc().nulls_last())
        .all()
    )
    waiting = (
        db.query(WaitingOn)
        .options(selectinload(WaitingOn.project))
        .order_by(WaitingOn.created_at.desc())
        .all()
    )
    rituals = db.query(RitualEntry).order_by(RitualEntry.created_at.desc()).all()

    return {
        "projects": [project_summary(p) for p in projects],
        "tasks": [task_summary(t) for t in tasks],
        "blocks": [block_summary(b) for b in blocks],
        "waiting_on": [waiting_summary(w) for w in waiting],
        "ritual_entries": [ritual_summary(r) for r in rituals],
    }


def build_coach_context(
    *,
    request_path: str,
    screen_id: str,
    screen_title: str,
    screen_data: dict[str, Any],
    global_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "screen": {
            "id": screen_id,
            "title": screen_title,
            "path": request_path,
        },
        "screen_data": screen_data,
        "lists": global_context,
        "generated_at": datetime.now().isoformat(),
    }


def build_coach_context_json(
    *,
    request_path: str,
    screen_id: str,
    screen_title: str,
    screen_data: dict[str, Any],
    db: Session,
) -> str:
    context = build_coach_context(
        request_path=request_path,
        screen_id=screen_id,
        screen_title=screen_title,
        screen_data=screen_data,
        global_context=collect_global_context(db),
    )
    payload = json.dumps(context, ensure_ascii=True, default=_json_default)
    return payload.replace("</", "<\\/")


def _quote_bank() -> list[str]:
    return [
        "Everything that matters is a project.",
        "Displacement is real: every yes displaces countless other yeses.",
        "No date = no finish.",
        "Plans create clarity, not certainty.",
        "Best work requires focus blocks and realistic capacity planning.",
        "Thrashing is normal; design for it.",
        "The Five Projects Rule prevents overload.",
        "Intention, Awareness, Boundaries, Courage, Discipline.",
    ]


def _maybe_quote(seed_text: str) -> str | None:
    if random.random() > _DEFAULT_QUOTE_CHANCE:
        return None
    quote = random.choice(_quote_bank())
    return f'Like I said in Start Finishing, "{quote}"'


def _cozi_screen_hint(screen_id: str) -> str | None:
    if screen_id in {"home", "week_calendar"}:
        return "Your calendar shows what you're protecting."
    return None


def _is_guide_request(text: str) -> bool:
    lowered = (text or "").lower()
    guide_phrases = (
        "how do i use",
        "how to use",
        "how does this app work",
        "how does this work",
        "getting started",
        "guide",
        "where should i start",
        "where do i start",
        "how do i start",
        "just starting",
        "just started",
        "i'm new",
        "im new",
        "new here",
        "no idea what i'm doing",
        "no idea what im doing",
        "don't know what i'm doing",
        "dont know what im doing",
        "not sure where to start",
        "i'm lost",
        "im lost",
        "confused",
        "overwhelmed",
        "walk me through",
        "show me how",
    )
    return any(phrase in lowered for phrase in guide_phrases)


def _is_goal_request(text: str) -> bool:
    lowered = (text or "").lower()
    goal_phrases = (
        "quarterly",
        "monthly goals",
        "weekly goals",
        "yearly goals",
        "annual goals",
        "goal setting",
    )
    return any(phrase in lowered for phrase in goal_phrases)


def coach_guide_reply() -> str:
    return (
        "Quick guide:\n"
        "- Capture tasks or projects (Quick capture or Guided capture).\n"
        "- Pick your weekly focus (4 work + 3 personal) in Weekly Review.\n"
        "- Schedule Focus/Admin/Social/Recovery blocks on the calendar.\n"
        "- Do a morning check-in, a midday reset, and an evening check-out.\n\n"
        "Tell me what you want to do and I’ll walk you through it."
    )


def _summarize_counts(context: dict[str, Any]) -> dict[str, int]:
    lists = context.get("lists", {}) if context else {}
    projects = lists.get("projects", [])
    tasks = lists.get("tasks", [])
    blocks = lists.get("blocks", [])
    waiting = lists.get("waiting_on", [])

    active_projects = [p for p in projects if p.get("active_this_week")]
    today_tasks = [t for t in tasks if t.get("when_bucket") == "today" and t.get("status") != "done"]
    unscheduled_tasks = [
        t
        for t in tasks
        if t.get("scheduled_for") in (None, "") and t.get("block_type") and t.get("duration_minutes")
    ]
    return {
        "projects_total": len(projects),
        "projects_active": len(active_projects),
        "tasks_total": len(tasks),
        "tasks_today": len(today_tasks),
        "blocks_total": len(blocks),
        "waiting_total": len(waiting),
        "unscheduled_ready": len(unscheduled_tasks),
    }


def coach_lite_reply(message: str, context: dict[str, Any] | None) -> str:
    screen = (context or {}).get("screen", {})
    screen_id = screen.get("id", "home")
    screen_title = screen.get("title", "your screen")
    counts = _summarize_counts(context or {})
    message_lower = (message or "").lower()

    if _is_goal_request(message):
        return (
            "You do not need quarterly goals to start. Pick one weekly focus and protect a Focus block, "
            "then refine the bigger goals as you go. What is one outcome you want by Friday?"
        )

    observations = []
    if counts["projects_active"] > 7:
        observations.append(
            f"You've got {counts['projects_active']} active projects this week. That's above your 4+3 boundary."
        )
    if counts["tasks_today"] > 6:
        observations.append(
            f"Today has {counts['tasks_today']} tasks listed. That's a lot for one day."
        )
    if counts["unscheduled_ready"] > 0 and screen_id in {"home", "blocks"}:
        observations.append(
            f"There are {counts['unscheduled_ready']} tasks ready to schedule into blocks."
        )
    if counts["waiting_total"] > 0 and screen_id in {"home", "waiting"}:
        observations.append(
            f"You've got {counts['waiting_total']} items waiting on others."
        )

    hard_truth = None
    if counts["projects_active"] > 7:
        hard_truth = "Straight up: you're overcommitted. Something has to wait."
    elif counts["tasks_today"] > 6:
        hard_truth = "Straight up: this list won't all happen today. Choose your One Thing."

    suggestion = None
    if screen_id == "blocks":
        suggestion = "Would you put one real block on the calendar, even if it's just 45 minutes?"
    elif screen_id in {"home", "week_calendar"}:
        home_suggestions = []
        if counts["tasks_total"] == 0 and counts["projects_total"] == 0:
            home_suggestions.append("Start with Quick capture to dump what's on your mind.")
        if counts["unscheduled_ready"] > 0:
            home_suggestions.append("Schedule one ready task into a Focus block so it has time.")
        if counts["blocks_total"] == 0:
            home_suggestions.append("Protect one Focus block first, then let admin fill the gaps.")
        suggestion = random.choice(home_suggestions) if home_suggestions else (
            "Protect one Focus block first, then let admin fill the gaps."
        )
    elif screen_id == "waiting":
        suggestion = "Would you schedule the next follow-up so it doesn't keep rattling around?"
    elif screen_id.startswith("ritual_"):
        suggestion = "Name the one thing that makes today a win. Keep it small and real."
    else:
        suggestion = "What is the next concrete step you can attach to time?"

    openers = [
        f"You're on {screen_title}.",
        f"Got it — {screen_title}.",
        f"{screen_title} in front of you.",
    ]
    questions = [
        "What do you want to make true in the next 90 minutes?",
        "What would make today feel finished?",
        "What's the one thing worth protecting today?",
    ]

    opener = random.choice(openers)
    insight = hard_truth or (observations[0] if observations else None)
    hint = None
    if not insight and "help" in message_lower:
        hint = _cozi_screen_hint(screen_id)

    quote = _maybe_quote(message) if "help" in message_lower else None

    sentences = [opener]
    if insight:
        sentences.append(insight)
    if hint:
        sentences.append(hint)
    if suggestion:
        sentences.append(suggestion)
    if quote and len(sentences) < 3:
        sentences.append(quote)
    sentences.append(random.choice(questions))

    return " ".join(sentences)


def _llm_provider() -> str:
    return os.getenv("SFO_LLM_PROVIDER", "auto").strip().lower()


def _ollama_url() -> str:
    return os.getenv("SFO_OLLAMA_URL", "http://localhost:11434").rstrip("/")


def _ollama_model() -> str:
    return os.getenv("SFO_OLLAMA_MODEL", "llama3.1:8b").strip()


def _llm_timeout() -> int:
    raw = os.getenv("SFO_LLM_TIMEOUT")
    if raw and raw.isdigit():
        return int(raw)
    return _DEFAULT_LLM_TIMEOUT


def _ollama_available() -> bool:
    url = f"{_ollama_url()}/api/tags"
    try:
        req = UrlRequest(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=2) as resp:
            if resp.status != 200:
                return False
        return True
    except Exception:
        return False


def _build_llm_messages(
    system_prompt: str,
    history: list[CoachMessage],
    new_message: str,
    context_json: str | None,
) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt}]
    recent = history[-12:] if history else []
    for msg in recent:
        content = msg.content
        if msg.role == "user" and msg.context_json:
            content = f"{content}\n\nContext:\n{msg.context_json}"
        messages.append({"role": msg.role, "content": content})
    if context_json:
        composed = f"{new_message}\n\nContext:\n{context_json}"
    else:
        composed = new_message
    messages.append({"role": "user", "content": composed})
    return messages


def _system_prompt() -> str:
    return (
        "You are Charlie Gilkey, the wise, direct coach from Start Finishing. "
        "You speak with calm authority, Kiwi-understated warmth, and honest candor. "
        "Sound like a real person, not a robot. "
        "You can push the user when needed, but never shame or belittle. "
        "Use curiosity and invitations, not commands. "
        "You give advice only; do not claim to take actions or change data. "
        "Use the provided context to comment on what the user is viewing. "
        "Focus on 1-2 salient details; do not list everything. "
        "Keep replies concise: 2-4 sentences, single paragraph, ~70 words max. "
        "Avoid lists unless the user explicitly asks for steps. "
        "If the user asks how to use the app, give a brief 3-5 step guide and offer to walk them through it. "
        "Ask one grounding question at the end. "
        "Use contractions and vary sentence length. "
        "If you include a quote, format it exactly as: Like I said in Start Finishing, \"...\""
    )


def _call_ollama(messages: list[dict[str, str]]) -> str:
    url = f"{_ollama_url()}/api/chat"
    payload = {
        "model": _ollama_model(),
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.6,
            "top_p": 0.9,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = UrlRequest(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=_llm_timeout()) as resp:
        body = resp.read()
    parsed = json.loads(body)
    return (parsed.get("message") or {}).get("content", "").strip()


def generate_coach_reply(
    *,
    message: str,
    context: dict[str, Any] | None,
    history: list[CoachMessage],
) -> tuple[str, list[dict[str, str]], str]:
    provider = _llm_provider()
    context_json = json.dumps(context, ensure_ascii=True, default=_json_default) if context else None
    actions = suggest_quick_actions(context)

    if _is_guide_request(message):
        return coach_guide_reply(), actions, "coach-lite"

    if provider == "off":
        return coach_lite_reply(message, context), actions, "coach-lite"

    if provider == "auto" and not _ollama_available():
        return coach_lite_reply(message, context), actions, "coach-lite"

    if provider in {"ollama", "auto"}:
        try:
            messages = _build_llm_messages(_system_prompt(), history, message, context_json)
            reply = _call_ollama(messages)
            if reply:
                return reply, actions, "ollama"
        except (URLError, HTTPError, TimeoutError, ValueError):
            pass
        except Exception:
            pass

    return coach_lite_reply(message, context), actions, "coach-lite"


def suggest_quick_actions(context: dict[str, Any] | None) -> list[dict[str, str]]:
    screen_id = ((context or {}).get("screen") or {}).get("id")
    actions: list[dict[str, str]] = []
    if screen_id == "home":
        actions = [
            {"label": "Add time block", "url": "/blocks#add-block"},
            {"label": "Quick capture", "url": "/capture"},
            {"label": "Week view", "url": "/calendar/week"},
        ]
    elif screen_id == "week_calendar":
        actions = [
            {"label": "Add time block", "url": "/blocks#add-block"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id in {"capture", "capture_wizard"}:
        actions = [
            {"label": "Back to Today", "url": "/"},
            {"label": "Week review", "url": "/weekly"},
        ]
    elif screen_id == "blocks":
        actions = [
            {"label": "Add time block", "url": "/blocks#add-block"},
            {"label": "Week view", "url": "/calendar/week"},
        ]
    elif screen_id == "resurface":
        actions = [
            {"label": "Weekly review", "url": "/weekly"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "weekly_review":
        actions = [
            {"label": "Resurface list", "url": "/resurface"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "waiting":
        actions = [
            {"label": "Quick capture", "url": "/capture"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "ritual_morning":
        actions = [
            {"label": "Midday reset", "url": "/ritual/midday"},
            {"label": "Evening check-out", "url": "/ritual/evening"},
        ]
    elif screen_id == "ritual_midday":
        actions = [
            {"label": "Morning check-in", "url": "/ritual/morning"},
            {"label": "Evening check-out", "url": "/ritual/evening"},
        ]
    elif screen_id == "ritual_evening":
        actions = [
            {"label": "Morning check-in", "url": "/ritual/morning"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "long_range":
        actions = [
            {"label": "Weekly review", "url": "/weekly"},
            {"label": "Quick capture", "url": "/capture"},
            {"label": "Back to Today", "url": "/"},
        ]
    return actions
