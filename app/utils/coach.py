from __future__ import annotations

import json
import os
import random
import re
from datetime import date, datetime, time
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy.orm import Session, selectinload

from ..models import Block, CoachMessage, Profile, Project, RitualEntry, Task, WaitingOn

_DEFAULT_QUOTE_CHANCE = 0.12
_DEFAULT_HISTORY_LIMIT = 120
_DEFAULT_LLM_TIMEOUT = 15
_DEFAULT_SCREEN_ITEM_LIMIT = 8
_DEFAULT_CONTEXT_PROJECT_LIMIT = 18
_DEFAULT_CONTEXT_TASK_LIMIT = 40
_DEFAULT_CONTEXT_BLOCK_LIMIT = 28
_DEFAULT_CONTEXT_WAITING_LIMIT = 20
_DEFAULT_CONTEXT_RITUAL_LIMIT = 12
_DEFAULT_TEXT_PREVIEW_LIMIT = 160
_DEFAULT_CONTEXT_MAX_BYTES = 120_000


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 500_000) -> int:
    raw = os.getenv(name)
    if not raw or not raw.isdigit():
        return default
    value = int(raw)
    return max(minimum, min(maximum, value))


def _to_iso(value: date | datetime | time | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value)


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _is_short_message(text: str) -> bool:
    cleaned = _normalize_text(text)
    if not cleaned:
        return False
    return len(cleaned.split()) <= 3


def _trim_list(items: list[Any], limit: int) -> tuple[list[Any], int]:
    if len(items) <= limit:
        return items, 0
    return items[:limit], len(items) - limit


def _trim_screen_data(screen_data: dict[str, Any], limit: int = 6) -> dict[str, Any]:
    trimmed: dict[str, Any] = {}
    for key, value in (screen_data or {}).items():
        if isinstance(value, list):
            subset, extra = _trim_list(value, limit)
            trimmed[key] = subset
            if extra:
                trimmed[f"{key}_more"] = extra
        else:
            trimmed[key] = value
    return trimmed


def _text_preview(value: str | None, max_len: int = _DEFAULT_TEXT_PREVIEW_LIMIT) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) <= max_len:
        return cleaned
    if max_len <= 3:
        return cleaned[:max_len]
    return f"{cleaned[: max_len - 3]}..."


def project_summary(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "title": _text_preview(project.title, 80),
        "category": project.category.value if project.category else None,
        "status": project.status.value if project.status else None,
        "size": project.size.value if project.size else None,
        "color_scheme": project.color_scheme,
        "time_horizon": project.time_horizon,
        "start_date": _to_iso(project.start_date),
        "target_date": _to_iso(project.target_date),
        "level_of_success": project.level_of_success.value if project.level_of_success else None,
        "why_link_text": _text_preview(project.why_link_text, 120),
        "active_this_week": project.active_this_week,
        "created_at": _to_iso(project.created_at),
    }


def task_summary(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "verb_noun": _text_preview(task.verb_noun, 100),
        "description": _text_preview(task.description, 220),
        "project_id": task.project_id,
        "project_title": _text_preview(task.project.title if task.project else None, 80),
        "in_inbox": task.in_inbox,
        "when_bucket": task.when_bucket.value if task.when_bucket else None,
        "block_type": task.block_type.value if task.block_type else None,
        "duration_minutes": task.duration_minutes,
        "priority": task.priority,
        "frog": task.frog,
        "alignment": task.alignment.value if task.alignment else None,
        "first_action": _text_preview(task.first_action, 120),
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
        "morning_right_now": entry.morning_right_now,
        "morning_email_plan": entry.morning_email_plan,
        "morning_focus_chunk": entry.morning_focus_chunk,
        "one_thing": entry.one_thing,
        "frog": entry.frog,
        "gratitude": entry.gratitude,
        "anticipation": entry.anticipation,
        "why_reflection": entry.why_reflection,
        "why_expanded": entry.why_expanded,
        "block_plan": entry.block_plan,
        "admin_plan": entry.admin_plan,
        "emotional_intent": entry.emotional_intent,
        "midday_alignment": entry.midday_alignment,
        "midday_surprises": entry.midday_surprises,
        "midday_one_thing": entry.midday_one_thing,
        "midday_frog": entry.midday_frog,
        "aar_went_well": entry.aar_went_well,
        "aar_hard": entry.aar_hard,
        "aar_next_step": entry.aar_next_step,
        "wins": entry.wins,
        "adjustments": entry.adjustments,
        "evening_shutdown": entry.evening_shutdown,
        "evening_breadcrumbs": entry.evening_breadcrumbs,
        "energy": entry.energy,
        "notes": entry.notes,
        "created_at": _to_iso(entry.created_at),
    }


def profile_summary(profile: Profile | None) -> dict[str, Any] | None:
    if not profile:
        return None
    return {
        "name": profile.name,
        "why_primary": profile.why_primary,
        "why_expanded": profile.why_expanded,
        "values_text": profile.values_text,
        "energy_profile": profile.energy_profile,
        "workday_start": _to_iso(profile.workday_start),
        "workday_end": _to_iso(profile.workday_end),
        "weekly_review_day": profile.weekly_review_day,
        "focus_block_preference": profile.focus_block_preference,
    }


def collect_global_context(db: Session) -> dict[str, Any]:
    project_limit = _env_int("SFO_COACH_CONTEXT_PROJECT_LIMIT", _DEFAULT_CONTEXT_PROJECT_LIMIT, maximum=300)
    task_limit = _env_int("SFO_COACH_CONTEXT_TASK_LIMIT", _DEFAULT_CONTEXT_TASK_LIMIT, maximum=500)
    block_limit = _env_int("SFO_COACH_CONTEXT_BLOCK_LIMIT", _DEFAULT_CONTEXT_BLOCK_LIMIT, maximum=500)
    waiting_limit = _env_int("SFO_COACH_CONTEXT_WAITING_LIMIT", _DEFAULT_CONTEXT_WAITING_LIMIT, maximum=300)
    ritual_limit = _env_int("SFO_COACH_CONTEXT_RITUAL_LIMIT", _DEFAULT_CONTEXT_RITUAL_LIMIT, maximum=120)

    profile = db.query(Profile).order_by(Profile.id.asc()).first()
    projects = (
        db.query(Project)
        .order_by(Project.active_this_week.desc(), Project.created_at.desc())
        .limit(project_limit)
        .all()
    )
    tasks = (
        db.query(Task)
        .options(selectinload(Task.project))
        .order_by(Task.created_at.desc())
        .limit(task_limit)
        .all()
    )
    blocks = (
        db.query(Block)
        .options(selectinload(Block.project))
        .order_by(Block.date.desc(), Block.start_time.desc().nulls_last())
        .limit(block_limit)
        .all()
    )
    waiting = (
        db.query(WaitingOn)
        .options(selectinload(WaitingOn.project))
        .order_by(WaitingOn.created_at.desc())
        .limit(waiting_limit)
        .all()
    )
    rituals = (
        db.query(RitualEntry)
        .order_by(RitualEntry.created_at.desc())
        .limit(ritual_limit)
        .all()
    )

    return {
        "profile": profile_summary(profile),
        "projects": [
            {
                "id": p.id,
                "title": _text_preview(p.title, 80),
                "category": p.category.value if p.category else None,
                "status": p.status.value if p.status else None,
                "time_horizon": p.time_horizon,
                "target_date": _to_iso(p.target_date),
                "active_this_week": p.active_this_week,
            }
            for p in projects
        ],
        "tasks": [
            {
                "id": t.id,
                "verb_noun": _text_preview(t.verb_noun, 100),
                "project_id": t.project_id,
                "project_title": _text_preview(t.project.title if t.project else None, 80),
                "in_inbox": t.in_inbox,
                "when_bucket": t.when_bucket.value if t.when_bucket else None,
                "block_type": t.block_type.value if t.block_type else None,
                "duration_minutes": t.duration_minutes,
                "status": t.status.value if t.status else None,
                "scheduled_for": _to_iso(t.scheduled_for),
                "frog": t.frog,
            }
            for t in tasks
        ],
        "blocks": [
            {
                "id": b.id,
                "title": _text_preview(b.title or "", 80) or None,
                "date": _to_iso(b.date),
                "start_time": _to_iso(b.start_time),
                "end_time": _to_iso(b.end_time),
                "block_type": b.block_type.value if b.block_type else None,
                "project_id": b.project_id,
                "project_title": _text_preview(b.project.title if b.project else None, 80),
            }
            for b in blocks
        ],
        "waiting_on": [
            {
                "id": w.id,
                "description": _text_preview(w.description, 100),
                "person": _text_preview(w.person, 60),
                "project_id": w.project_id,
                "project_title": _text_preview(w.project.title if w.project else None, 80),
                "last_followup": _to_iso(w.last_followup),
            }
            for w in waiting
        ],
        "ritual_entries": [
            {
                "id": r.id,
                "ritual_type": r.ritual_type.value if r.ritual_type else None,
                "entry_date": _to_iso(r.entry_date),
                "one_thing": _text_preview(r.one_thing, 100),
                "frog": _text_preview(r.frog, 100),
                "wins": _text_preview(r.wins, 120),
            }
            for r in rituals
        ],
    }


def build_coach_context(
    *,
    request_path: str,
    screen_id: str,
    screen_title: str,
    screen_data: dict[str, Any],
    global_context: dict[str, Any],
) -> dict[str, Any]:
    screen_limit = _env_int(
        "SFO_COACH_SCREEN_ITEM_LIMIT",
        _DEFAULT_SCREEN_ITEM_LIMIT,
        minimum=1,
        maximum=40,
    )
    return {
        "screen": {
            "id": screen_id,
            "title": screen_title,
            "path": request_path,
        },
        "screen_data": _trim_screen_data(screen_data, limit=screen_limit),
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
    max_bytes = _env_int(
        "SFO_COACH_CONTEXT_MAX_BYTES",
        _DEFAULT_CONTEXT_MAX_BYTES,
        minimum=20_000,
        maximum=500_000,
    )
    if len(payload.encode("utf-8")) > max_bytes:
        context["lists"] = {"profile": context.get("lists", {}).get("profile")}
        context["screen_data"] = _trim_screen_data(context.get("screen_data", {}), limit=4)
        context["context_notice"] = "trimmed_for_size"
        payload = json.dumps(context, ensure_ascii=True, default=_json_default)
    return payload.replace("</", "<\\/")


def _context_for_llm(context: dict[str, Any] | None) -> str | None:
    if not context:
        return None
    lists = context.get("lists", {}) if isinstance(context, dict) else {}
    digest: dict[str, Any] = {
        "screen": context.get("screen", {}),
        "screen_data": _trim_screen_data(context.get("screen_data", {})),
        "counts": _summarize_counts(context),
    }
    if isinstance(lists, dict) and lists.get("profile"):
        digest["profile"] = lists["profile"]
    return json.dumps(digest, ensure_ascii=True, default=_json_default)


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
        "help me with what i'm looking at",
        "help me with what im looking at",
        "help with this",
        "what should i do",
        "what do i do",
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


def _is_greeting(text: str) -> bool:
    cleaned = _normalize_text(text)
    if not cleaned:
        return False
    tokens = cleaned.split()
    if len(tokens) > 3:
        return False
    base = {"hello", "hi", "hey", "hiya", "yo", "sup", "gday"}
    if cleaned in {"good morning", "good afternoon", "good evening", "kia ora"}:
        return True
    if len(tokens) == 1 and tokens[0] in base:
        return True
    if len(tokens) == 2 and tokens[0] in base and tokens[1] in {"there", "charlie"}:
        return True
    return False


def _screen_playbook(screen_id: str) -> str | None:
    if screen_id == "home":
        return (
            "Let's keep it simple: first capture what's on your mind, then choose your One Thing, "
            "then protect one Focus block on the calendar. Want me to help pick the One Thing?"
        )
    if screen_id == "week_calendar":
        return (
            "Scan the week, protect one Focus block for your top project, then let admin fill the gaps. "
            "Which day should we lock in first?"
        )
    if screen_id in {"capture", "capture_wizard"}:
        return (
            "Capture in one pass: name the thing, decide task vs project, then set its time horizon. "
            "Do you want to capture a project or a task right now?"
        )
    if screen_id == "blocks":
        return (
            "Start with one Focus block, then assign a task, then add an admin block around it. "
            "What time window should we protect?"
        )
    if screen_id == "resurface":
        return (
            "Pull anything due into this week, reset dates for the rest, then pick one to schedule. "
            "Which item feels ready now?"
        )
    if screen_id == "weekly_review":
        return (
            "Use this to pick your 4+3 weekly focus and resurface tasks; if you want a guided flow, open the wizard. "
            "Want to start with focus projects or resurfacing?"
        )
    if screen_id == "weekly_wizard":
        return (
            "Follow the steps in order: note wins, pick weekly focus, resurface, plan blocks, then archive + reflect. "
            "Ready for step one?"
        )
    if screen_id == "waiting":
        return (
            "Set a follow-up date for each OPP, then capture anything new waiting on others. "
            "Who needs a follow-up first?"
        )
    if screen_id.startswith("ritual_"):
        return (
            "Keep it light: answer the prompts honestly, then choose one small adjustment. "
            "Want to do that now?"
        )
    if screen_id == "long_range":
        return (
            "Touch the pyramid, confirm horizons, then refine one project. "
            "Which horizon needs attention?"
        )
    if screen_id == "tasks":
        return (
            "Switch between time and project views, edit one task to set when + block type, then mark done and archive weekly. "
            "Which task should we tighten first?"
        )
    if screen_id == "profile":
        return (
            "Keep it short: update your Why and energy profile, then save. "
            "Want help drafting the Why in one sentence?"
        )
    if screen_id == "onboarding":
        return (
            "Go step by step: name + Why, values, energy/workday, then seed weekly projects. "
            "Ready for step one?"
        )
    if screen_id == "export":
        return (
            "Pick a time range, tick the data sets you want (defaults exclude some), then export to download JSON + CSV. "
            "Which time window do you want?"
        )
    if screen_id == "health_dashboard":
        return (
            "Log a quick metric or blood pressure, set a goal, then open a focus area for deeper tracking. "
            "Want to start with a quick log or a goal?"
        )
    if screen_id.startswith("health_"):
        return (
            "Log today's measurement, scan the trend cards, then adjust your next small goal. "
            "Want to log a data point now?"
        )
    return None


def coach_guide_reply() -> str:
    return (
        "Quick guide: capture tasks or projects, pick weekly focus (4 work + 3 personal), "
        "schedule Focus/Admin/Social/Recovery blocks, and close the day with a ritual. "
        "Tell me what you want to do and I'll walk you through it."
    )


def coach_help_reply(context: dict[str, Any] | None) -> str:
    screen = (context or {}).get("screen", {})
    screen_id = screen.get("id", "home")
    screen_data = (context or {}).get("screen_data", {})
    if screen_id == "home" and isinstance(screen_data, dict):
        inbox_tasks = screen_data.get("inbox_tasks", [])
        today_tasks = screen_data.get("today_tasks", [])
        current_block = screen_data.get("current_block")
        if isinstance(inbox_tasks, list) and inbox_tasks:
            title = inbox_tasks[0].get("verb_noun") or "an inbox item"
            return (
                "You're on Home. Start with the Inbox: process "
                f"\"{title}\" by deciding task vs project, then give it a time bucket. "
                "Want me to guide that one?"
            )
        if isinstance(today_tasks, list) and today_tasks:
            title = today_tasks[0].get("verb_noun") or "a task"
            return (
                "You're on Home. Pick one task for today, then protect a Focus block for it. "
                f"For example, \"{title}\" could be your One Thing. Want help choosing?"
            )
        if isinstance(current_block, dict) and current_block.get("title"):
            title = current_block.get("title")
            return (
                f"You're on Home. Your current block is \"{title}\"; protect the time and "
                "attach one task so it stays concrete. Want to do that now?"
            )
    if screen_id == "tasks" and isinstance(screen_data, dict):
        tasks = screen_data.get("tasks", [])
        if isinstance(tasks, list) and tasks:
            title = tasks[0].get("verb_noun") or "a task"
            return (
                "You're on Tasks. Tighten one task by setting when plus block type so it can be scheduled. "
                f"Want to start with \"{title}\"?"
            )
    playbook = _screen_playbook(screen_id)
    if playbook:
        return playbook
    return coach_guide_reply()


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


def _candidate_tasks(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not context:
        return []
    screen_data = context.get("screen_data", {}) if isinstance(context, dict) else {}
    tasks: list[dict[str, Any]] = []
    for key in ("inbox_tasks", "today_tasks", "tasks"):
        items = screen_data.get(key, [])
        if isinstance(items, list):
            tasks.extend([item for item in items if isinstance(item, dict)])
    if not tasks:
        lists = context.get("lists", {}) if isinstance(context, dict) else {}
        items = lists.get("tasks", [])
        if isinstance(items, list):
            tasks.extend([item for item in items if isinstance(item, dict)])
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task in tasks:
        key = str(task.get("id") or task.get("verb_noun") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(task)
    return deduped


def _match_task_in_message(message: str, context: dict[str, Any] | None) -> dict[str, Any] | None:
    msg = _normalize_text(message)
    if not msg:
        return None
    msg_words = set(msg.split())
    for task in _candidate_tasks(context):
        name = _normalize_text(task.get("verb_noun") or "")
        if not name:
            continue
        if name in msg:
            return task
        name_words = set(name.split())
        if name_words and name_words.issubset(msg_words):
            return task
    return None


def _task_guidance_reply(task: dict[str, Any]) -> str | None:
    title = task.get("verb_noun") or "That item"
    in_inbox = bool(task.get("in_inbox"))
    when_bucket = task.get("when_bucket")
    block_type = task.get("block_type")
    duration = task.get("duration_minutes")
    scheduled_for = task.get("scheduled_for")

    if in_inbox:
        return (
            f"\"{title}\" is sitting in your Inbox. Decide if it's a task (15-120 min) or a project. "
            "If it's a task, give it a rough duration and when it should surface; if it's a project, "
            "set a horizon and a next action. Which is it?"
        )

    if not when_bucket:
        return (
            f"\"{title}\" needs a time bucket so it shows up in the right view. "
            "Is it today, this week, this month, or later?"
        )

    if not block_type or not duration:
        return (
            f"\"{title}\" needs a block type and rough duration before it can land on the calendar. "
            "Pick Focus vs Admin and estimate minutes. Want me to suggest a default?"
        )

    if not scheduled_for and when_bucket in {"today", "week"}:
        return (
            f"\"{title}\" is set for {when_bucket}. Put a block on the calendar so it has real time. "
            "Do you want to schedule it now?"
        )

    return (
        f"\"{title}\" looks ready. What's the single next step you want to protect first?"
    )


def coach_lite_reply(message: str, context: dict[str, Any] | None) -> str:
    screen = (context or {}).get("screen", {})
    screen_id = screen.get("id", "home")
    screen_title = screen.get("title", "your screen")
    screen_data = (context or {}).get("screen_data", {})
    counts = _summarize_counts(context or {})
    message_lower = (message or "").lower()
    inbox_count = 0
    if isinstance(screen_data, dict):
        inbox_tasks = screen_data.get("inbox_tasks", [])
        if isinstance(inbox_tasks, list):
            inbox_count = len(inbox_tasks)

    if _is_goal_request(message):
        return (
            "You do not need quarterly goals to start. Pick one weekly focus and protect a Focus block, "
            "then refine the bigger goals as you go. What is one outcome you want by Friday?"
        )

    if _is_greeting(message):
        if screen_id == "home":
            return (
                "Hey — good to see you. You're on Home. Want help with the Inbox or picking your One Thing?"
            )
        return f"Hey — good to see you. You're on {screen_title}. Want help with what's on this screen?"

    task_match = _match_task_in_message(message, context)
    if task_match:
        reply = _task_guidance_reply(task_match)
        if reply:
            return reply

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
    if counts["waiting_total"] > 0 and (
        screen_id == "waiting" or "waiting" in message_lower or "opp" in message_lower
    ):
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
    elif screen_id == "tasks":
        suggestion = "Pick one task to tighten: set when + block type so it can get time."
    elif screen_id == "weekly_wizard":
        suggestion = "Stay with step one: name the wins that actually moved the week."
    elif screen_id == "weekly_review":
        suggestion = "Pick 4 work + 3 personal projects to keep the week honest."
    elif screen_id == "profile":
        suggestion = "Short Why, clear energy profile, then save. Keep it human."
    elif screen_id == "onboarding":
        suggestion = "Step one only: name + Why. We'll handle the rest after."
    elif screen_id == "export":
        suggestion = "Choose a time window, tick the data sets you want, then export."
    elif screen_id == "health_dashboard":
        suggestion = "Log one data point to keep momentum, then set a single goal."
    elif screen_id.startswith("health_"):
        suggestion = "Log today's measurement, then glance at the trend card."
    elif screen_id in {"home", "week_calendar"}:
        home_suggestions = []
        if counts["tasks_total"] == 0 and counts["projects_total"] == 0:
            home_suggestions.append("Start with Quick capture to dump what's on your mind.")
        if inbox_count > 0:
            home_suggestions.append("Process one Inbox item so it has a home.")
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
    elif screen_id == "long_range":
        suggestion = "Focus one horizon at a time. Which level matters most right now?"
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


def _llm_history_limit() -> int:
    raw = os.getenv("SFO_LLM_HISTORY_LIMIT")
    if raw and raw.isdigit():
        return max(1, int(raw))
    return 6


def _llm_max_tokens() -> int:
    raw = os.getenv("SFO_LLM_MAX_TOKENS")
    if raw and raw.isdigit():
        return max(60, int(raw))
    return 160


def _llm_shortcuts_enabled() -> bool:
    raw = os.getenv("SFO_LLM_SHORTCUTS")
    if raw is None:
        return True
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
    if context_json:
        messages.append(
            {"role": "system", "content": f"Context JSON (read-only):\n{context_json}"}
        )
    recent = history[-_llm_history_limit():] if history else []
    for msg in recent:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": new_message})
    return messages


def _system_prompt() -> str:
    return (
        "You are Charlie Gilkey, the wise, direct coach from Start Finishing. "
        "You speak with calm authority, Kiwi-understated warmth, and honest candor. "
        "Sound like a real person, not a robot. "
        "You can push the user when needed, but never shame or belittle. "
        "Use curiosity and invitations, not commands. "
        "You give advice only; do not claim to take actions or change data. "
        "Use the provided context JSON as your ground truth about the user's screen and data. "
        "Use the current screen to anchor your guidance. "
        "If the user mentions a specific task, project, or block, look for it in the context and respond about that item; "
        "if you cannot find it, ask a clarifying question. "
        "When the user asks for help on the current screen, guide them with one step at a time and keep it light. "
        "Avoid generic app tours unless the user asks how to use the app or says they're lost. "
        "Focus on 1-2 salient details; do not list everything. "
        "Keep replies concise: 2-4 sentences, single paragraph, ~70 words max. "
        "Avoid lists unless the user explicitly asks for steps. "
        "If the user asks how to use the app, give a brief 3-5 step guide and offer to walk them through it. "
        "Ask one grounding question at the end. "
        "Use contractions and vary sentence length. "
        "If you include a quote, format it exactly as: Like I said in Start Finishing, \"...\""
    )


def _heuristic_capture_kind(
    *,
    details: str,
    size: str | None,
    next_action: str | None,
    title: str | None,
) -> tuple[str, str]:
    if size == "multi" or next_action == "no":
        return "project", "Multiple steps or an unclear next action usually means project."
    if size == "single" and next_action == "yes":
        return "task", "Single sitting with a clear next step usually means task."

    text = _normalize_text(f"{title or ''} {details}")
    project_keywords = {
        "plan",
        "strategy",
        "research",
        "build",
        "design",
        "launch",
        "campaign",
        "roadmap",
        "rollout",
        "rebrand",
        "system",
        "process",
        "program",
        "initiative",
        "project",
        "multi",
        "multiple",
        "phases",
        "phase",
    }
    task_keywords = {
        "call",
        "email",
        "reply",
        "book",
        "schedule",
        "buy",
        "fix",
        "draft",
        "review",
        "send",
        "submit",
        "update",
        "finish",
        "write",
        "clean",
    }
    if any(word in text for word in project_keywords):
        return "project", "Sounds like multi-step work with moving parts."
    if any(word in text for word in task_keywords):
        return "task", "Looks like a single clear action."
    return "task", "Looks like a small, single-sitting action you can adjust later."


def suggest_capture_kind(
    *,
    details: str,
    size: str | None = None,
    next_action: str | None = None,
    title: str | None = None,
) -> tuple[str, str, str]:
    provider = _llm_provider()
    details = details.strip()
    prompt = (
        "Classify if the item is best treated as a TASK or PROJECT.\n"
        "Task = single sitting (15-120 min) with a clear next action.\n"
        "Project = multi-step, multiple sessions, or unclear next action.\n"
        "Reply with 'Task' or 'Project' on the first line, and one short reason on the second line."
    )
    payload = (
        f"Title: {title or ''}\n"
        f"Details: {details}\n"
        f"Single sitting?: {size or 'unknown'}\n"
        f"Next action clear?: {next_action or 'unknown'}"
    )

    if provider == "off":
        kind, rationale = _heuristic_capture_kind(
            details=details,
            size=size,
            next_action=next_action,
            title=title,
        )
        return kind, rationale, "heuristic"

    if provider == "auto" and not _ollama_available():
        kind, rationale = _heuristic_capture_kind(
            details=details,
            size=size,
            next_action=next_action,
            title=title,
        )
        return kind, rationale, "heuristic"

    if provider in {"ollama", "auto"}:
        try:
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": payload},
            ]
            reply = _call_ollama(messages)
            if reply:
                lines = [line.strip() for line in reply.splitlines() if line.strip()]
                first = lines[0].lower() if lines else ""
                kind = "project" if "project" in first else "task" if "task" in first else ""
                rationale = ""
                if len(lines) > 1:
                    rationale = lines[1]
                elif " - " in lines[0]:
                    rationale = lines[0].split(" - ", 1)[1].strip()
                elif ": " in lines[0]:
                    rationale = lines[0].split(": ", 1)[1].strip()
                if kind:
                    return kind, rationale or "You can still choose either way.", "ollama"
        except (URLError, HTTPError, TimeoutError, ValueError):
            pass
        except Exception:
            pass

    kind, rationale = _heuristic_capture_kind(
        details=details,
        size=size,
        next_action=next_action,
        title=title,
    )
    return kind, rationale, "heuristic"


def _call_ollama(messages: list[dict[str, str]]) -> str:
    url = f"{_ollama_url()}/api/chat"
    payload = {
        "model": _ollama_model(),
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.6,
            "top_p": 0.9,
            "num_predict": _llm_max_tokens(),
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = UrlRequest(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=_llm_timeout()) as resp:
        body = resp.read()
    parsed = json.loads(body)
    return (parsed.get("message") or {}).get("content", "").strip()


def refine_nudge_text(body: str) -> str:
    provider = _llm_provider()
    if provider == "off":
        return body
    if provider == "auto" and not _ollama_available():
        return body
    if provider not in {"ollama", "auto"}:
        return body
    prompt = (
        "Rewrite the coach insight below in Charlie's voice. "
        "Keep it concise (1-2 sentences, <= 40 words). "
        "No bullets or lists. End with a gentle invitation."
    )
    try:
        reply = _call_ollama(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": body},
            ]
        )
        return reply or body
    except (URLError, HTTPError, TimeoutError, ValueError):
        return body
    except Exception:
        return body


def generate_coach_reply(
    *,
    message: str,
    context: dict[str, Any] | None,
    history: list[CoachMessage],
) -> tuple[str, list[dict[str, str]], str]:
    provider = _llm_provider()
    llm_context_json = _context_for_llm(context)
    actions = suggest_quick_actions(context)

    if _llm_shortcuts_enabled() and _is_short_message(message):
        return coach_lite_reply(message, context), actions, "coach-lite"

    if _is_guide_request(message):
        if provider in {"ollama", "auto"}:
            if provider != "auto" or _ollama_available():
                try:
                    messages = _build_llm_messages(
                        _system_prompt(),
                        history,
                        message,
                        llm_context_json,
                    )
                    reply = _call_ollama(messages)
                    if reply:
                        return reply, actions, "ollama"
                except (URLError, HTTPError, TimeoutError, ValueError):
                    pass
                except Exception:
                    pass
        return coach_help_reply(context), actions, "coach-lite"

    if provider == "off":
        return coach_lite_reply(message, context), actions, "coach-lite"

    if provider == "auto" and not _ollama_available():
        return coach_lite_reply(message, context), actions, "coach-lite"

    if provider in {"ollama", "auto"}:
        try:
            messages = _build_llm_messages(_system_prompt(), history, message, llm_context_json)
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
            {"label": "Start wizard", "url": "/weekly/wizard"},
            {"label": "Resurface list", "url": "/resurface"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "weekly_wizard":
        actions = [
            {"label": "Add focus block", "url": "/blocks#add-block"},
            {"label": "Tasks board", "url": "/tasks"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "tasks":
        actions = [
            {"label": "Weekly review", "url": "/weekly/wizard"},
            {"label": "Quick capture", "url": "/capture"},
            {"label": "Add time block", "url": "/blocks#add-block"},
        ]
    elif screen_id == "profile":
        actions = [
            {"label": "Onboarding wizard", "url": "/onboarding"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "onboarding":
        actions = [
            {"label": "Profile", "url": "/profile"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "export":
        actions = [
            {"label": "Health dashboard", "url": "/health"},
            {"label": "Tasks board", "url": "/tasks"},
            {"label": "Back to Today", "url": "/"},
        ]
    elif screen_id == "health_dashboard":
        actions = [
            {"label": "Diet page", "url": "/health/diet"},
            {"label": "Fitness page", "url": "/health/fitness"},
            {"label": "Export data", "url": "/export"},
        ]
    elif screen_id and screen_id.startswith("health_"):
        actions = [
            {"label": "Health dashboard", "url": "/health"},
            {"label": "Export data", "url": "/export"},
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
