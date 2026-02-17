from __future__ import annotations

from datetime import datetime, timezone

from ..models import (
    Task,
    TaskStatus,
    WhenBucket,
    INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_PARK_LET_GO,
    INBOX_INTENT_SUPPORT_PROJECT,
    INBOX_INTENT_UNPROCESSED,
)


VALID_INBOX_INTENTS = {
    INBOX_INTENT_SUPPORT_PROJECT,
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_PARK_LET_GO,
}

QUICK_ROUTE_INTENTS = {
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_ENJOY_RECOVER,
    INBOX_INTENT_PARK_LET_GO,
}

INBOX_INTENT_LABELS = {
    INBOX_INTENT_SUPPORT_PROJECT: "Support a Project",
    INBOX_INTENT_LEARN_EXPLORE: "Learning",
    INBOX_INTENT_ENJOY_RECOVER: "Enjoy",
    INBOX_INTENT_PARK_LET_GO: "Parked",
    INBOX_INTENT_UNPROCESSED: "Unprocessed",
}


def normalize_inbox_intent(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized if normalized in VALID_INBOX_INTENTS else None


def apply_inbox_container(task: Task, intent: str) -> None:
    """Move an inbox task into a non-work container."""
    if intent not in QUICK_ROUTE_INTENTS:
        raise ValueError(f"Unsupported quick-route intent: {intent}")
    task.in_inbox = False
    task.when_bucket = WhenBucket.LATER
    task.intake_intent = intent
    task.intake_container = intent
    task.intake_processed_at = datetime.now(timezone.utc)
    task.project_id = None
    task.block_type = None
    task.duration_minutes = None
    task.frog = False
    task.alignment = None
    task.resurface_on = None
    task.completed_at = None
    task.status = TaskStatus.PENDING
    task.archived_from_inbox = False


def mark_support_project_processed(task: Task) -> None:
    task.intake_intent = INBOX_INTENT_SUPPORT_PROJECT
    task.intake_container = INBOX_INTENT_SUPPORT_PROJECT
    task.intake_processed_at = datetime.now(timezone.utc)


def reset_to_unprocessed_inbox(task: Task) -> None:
    task.in_inbox = True
    task.archived_from_inbox = False
    task.when_bucket = WhenBucket.LATER
    task.status = TaskStatus.PENDING
    task.completed_at = None
    task.intake_intent = INBOX_INTENT_UNPROCESSED
    task.intake_container = INBOX_INTENT_UNPROCESSED
    task.intake_processed_at = None
