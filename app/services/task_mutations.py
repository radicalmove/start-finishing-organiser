from __future__ import annotations

from app.models import (
    Alignment,
    Task,
    TaskStatus,
    WhenBucket,
)
from app.utils.inbox_intents import QUICK_ROUTE_INTENTS, reset_to_unprocessed_inbox
from app.utils.rules import parse_block_type, parse_optional_int
from app.utils.time import utc_now


_UNSET = object()


def _coerce_project_id(project_id: str | int | None) -> int | None:
    if project_id in (None, "", "null"):
        return None
    if isinstance(project_id, int):
        return project_id
    cleaned = str(project_id).strip()
    if not cleaned or cleaned == "null":
        return None
    return int(cleaned)


def _coerce_when_bucket(when_bucket: WhenBucket | str | None) -> WhenBucket | None:
    if when_bucket is None:
        return None
    if isinstance(when_bucket, WhenBucket):
        return when_bucket
    return WhenBucket(when_bucket)


def _coerce_alignment(alignment: Alignment | str | None) -> Alignment | None:
    if not alignment:
        return None
    if isinstance(alignment, Alignment):
        return alignment
    return Alignment(alignment)


def _normalize_description(description: str | None) -> str | None:
    if description is None:
        return None
    cleaned = description.strip()
    return cleaned or None


def _normalize_verb_noun(verb_noun: str | None) -> str | None:
    if verb_noun is None:
        return None
    cleaned = verb_noun.strip()
    return cleaned or None


def _has_inbox_undo_semantics(task: Task) -> bool:
    return bool(task.archived_from_inbox or task.intake_container in QUICK_ROUTE_INTENTS)


def apply_task_update(
    task: Task,
    *,
    verb_noun: str | None = None,
    description: str | None = None,
    project_id: str | int | object = _UNSET,
    when_bucket: WhenBucket | str | object = _UNSET,
    block_type: str | object = _UNSET,
    duration_minutes: str | int | object = _UNSET,
    frog: bool | object = _UNSET,
    alignment: Alignment | str | object = _UNSET,
    send_to_inbox: bool = False,
) -> Task:
    cleaned_title = _normalize_verb_noun(verb_noun)
    if cleaned_title is not None:
        task.verb_noun = cleaned_title

    if description is not None:
        task.description = _normalize_description(description)

    if project_id is not _UNSET:
        task.project_id = _coerce_project_id(project_id)

    if when_bucket is not _UNSET:
        cleaned_bucket = _coerce_when_bucket(when_bucket)
        if cleaned_bucket is not None:
            task.when_bucket = cleaned_bucket

    if block_type is not _UNSET:
        if block_type not in (None, "", "null"):
            task.block_type = parse_block_type(block_type)
        else:
            task.block_type = None

    if duration_minutes is not _UNSET:
        duration_value = parse_optional_int(None if duration_minutes is None else str(duration_minutes))
        if duration_value is not None and duration_value <= 0:
            duration_value = None
        task.duration_minutes = duration_value

    if frog is not _UNSET:
        task.frog = bool(frog)

    if alignment is not _UNSET:
        task.alignment = _coerce_alignment(alignment)

    if send_to_inbox:
        reset_to_unprocessed_inbox(task)

    return task


def complete_task(task: Task) -> Task:
    task.status = TaskStatus.DONE
    task.completed_at = utc_now()
    task.in_inbox = False
    return task


def reopen_task(task: Task) -> Task:
    task.status = TaskStatus.PENDING
    task.completed_at = None
    return task


def archive_task(task: Task) -> Task:
    task.status = TaskStatus.ARCHIVED
    task.in_inbox = False
    task.archived_from_inbox = False
    return task


def restore_task(task: Task) -> Task:
    task.status = TaskStatus.PENDING
    task.completed_at = None
    if task.archived_from_inbox:
        reset_to_unprocessed_inbox(task)
    else:
        task.in_inbox = False
    return task


def archive_inbox_task(task: Task) -> Task:
    reset_to_unprocessed_inbox(task)
    task.status = TaskStatus.ARCHIVED
    task.in_inbox = False
    task.archived_from_inbox = True
    task.completed_at = utc_now()
    return task


def restore_inbox_item(task: Task) -> Task:
    if not _has_inbox_undo_semantics(task):
        raise ValueError("Task does not have inbox restore semantics")
    reset_to_unprocessed_inbox(task)
    return task
