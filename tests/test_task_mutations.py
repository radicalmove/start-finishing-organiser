from datetime import datetime, timezone

import pytest

from app.models import (
    Alignment,
    BlockType,
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_UNPROCESSED,
    Project,
    Task,
    TaskStatus,
    WhenBucket,
)
import app.services.task_mutations as task_mutations


def _seed_task(db_session, **kwargs) -> Task:
    task_data = {
        "verb_noun": "Original title",
        "description": "Original description",
        "status": TaskStatus.PENDING,
        "when_bucket": WhenBucket.TODAY,
    }
    task_data.update(kwargs)
    task = Task(**task_data)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_update_task_normalizes_text_and_values(db_session):
    project = Project(title="Project A")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = _seed_task(db_session)

    task_mutations.apply_task_update(
        task,
        verb_noun="  Revised title  ",
        description="  Revised description  ",
        project_id=str(project.id),
        block_type="focus",
        duration_minutes="45",
        frog=True,
        alignment="aligned",
    )

    assert task.verb_noun == "Revised title"
    assert task.description == "Revised description"
    assert task.project_id == project.id
    assert task.block_type == BlockType.FOCUS
    assert task.duration_minutes == 45
    assert task.frog is True
    assert task.alignment == Alignment.ALIGNED
    assert task.when_bucket == WhenBucket.TODAY


def test_update_task_description_only_preserves_unrelated_fields(db_session):
    project = Project(title="Project A")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = _seed_task(
        db_session,
        project_id=project.id,
        block_type=BlockType.ADMIN,
        duration_minutes=30,
        frog=True,
        alignment=Alignment.UNALIGNED,
        when_bucket=WhenBucket.WEEK,
    )

    task_mutations.apply_task_update(task, description="  new  ")

    assert task.description == "new"
    assert task.project_id == project.id
    assert task.block_type == BlockType.ADMIN
    assert task.duration_minutes == 30
    assert task.frog is True
    assert task.alignment == Alignment.UNALIGNED
    assert task.when_bucket == WhenBucket.WEEK
    assert task.verb_noun == "Original title"


@pytest.mark.parametrize("project_id", ["", "null"])
def test_update_task_treats_blank_project_ids_as_unset(db_session, project_id):
    project = Project(title="Project A")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    task = _seed_task(db_session, project_id=project.id)

    task_mutations.apply_task_update(task, project_id=project_id)

    assert task.project_id is None


def test_update_task_send_to_inbox_resets_unprocessed_state(db_session):
    task = _seed_task(
        db_session,
        in_inbox=False,
        archived_from_inbox=True,
        status=TaskStatus.DONE,
        completed_at=datetime.now(timezone.utc),
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc),
        when_bucket=WhenBucket.MONTH,
    )

    task_mutations.apply_task_update(task, send_to_inbox=True)

    assert task.in_inbox is True
    assert task.archived_from_inbox is False
    assert task.status == TaskStatus.PENDING
    assert task.when_bucket == WhenBucket.LATER
    assert task.completed_at is None
    assert task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert task.intake_container == INBOX_INTENT_UNPROCESSED
    assert task.intake_processed_at is None


def test_complete_task_sets_done_and_stamps_completed_at(db_session):
    task = _seed_task(db_session, in_inbox=True)

    task_mutations.complete_task(task)

    assert task.status == TaskStatus.DONE
    assert task.in_inbox is False
    assert task.completed_at is not None


def test_reopen_task_clears_completed_at_and_returns_to_pending(db_session):
    task = _seed_task(
        db_session,
        status=TaskStatus.DONE,
        completed_at=datetime.now(timezone.utc),
    )

    task_mutations.reopen_task(task)

    assert task.status == TaskStatus.PENDING
    assert task.completed_at is None


def test_archive_task_clears_inbox_and_recycle_flag(db_session):
    task = _seed_task(
        db_session,
        in_inbox=True,
        archived_from_inbox=True,
        intake_intent="learn_explore",
        intake_container="learn_explore",
        intake_processed_at=datetime.now(timezone.utc),
    )

    task_mutations.archive_task(task)

    assert task.status == TaskStatus.ARCHIVED
    assert task.in_inbox is False
    assert task.archived_from_inbox is False
    assert task.intake_intent == "learn_explore"
    assert task.intake_container == "learn_explore"
    assert task.intake_processed_at is not None


def test_restore_task_respects_archived_from_inbox(db_session):
    recycle_task = _seed_task(
        db_session,
        status=TaskStatus.ARCHIVED,
        in_inbox=False,
        archived_from_inbox=True,
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc),
    )

    task_mutations.restore_task(recycle_task)

    assert recycle_task.status == TaskStatus.PENDING
    assert recycle_task.in_inbox is True
    assert recycle_task.archived_from_inbox is False
    assert recycle_task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert recycle_task.intake_container == INBOX_INTENT_UNPROCESSED
    assert recycle_task.intake_processed_at is None


def test_restore_task_keeps_non_recycle_task_out_of_inbox(db_session):
    regular_task = _seed_task(
        db_session,
        status=TaskStatus.ARCHIVED,
        in_inbox=False,
        archived_from_inbox=False,
    )

    task_mutations.restore_task(regular_task)

    assert regular_task.status == TaskStatus.PENDING
    assert regular_task.in_inbox is False
    assert regular_task.archived_from_inbox is False


def test_restore_task_clears_inbox_origin_metadata(db_session):
    task = _seed_task(
        db_session,
        status=TaskStatus.ARCHIVED,
        in_inbox=False,
        archived_from_inbox=True,
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc),
    )

    task_mutations.restore_task(task)

    assert task.status == TaskStatus.PENDING
    assert task.in_inbox is True
    assert task.archived_from_inbox is False
    assert task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert task.intake_container == INBOX_INTENT_UNPROCESSED
    assert task.intake_processed_at is None


def test_archive_inbox_task_sets_recycle_bin_state(db_session):
    task = _seed_task(
        db_session,
        in_inbox=True,
        archived_from_inbox=False,
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc),
    )

    task_mutations.archive_inbox_task(task)

    assert task.status == TaskStatus.ARCHIVED
    assert task.in_inbox is False
    assert task.archived_from_inbox is True
    assert task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert task.intake_container == INBOX_INTENT_UNPROCESSED
    assert task.intake_processed_at is None


def test_restore_inbox_item_restores_unprocessed_inbox_state(db_session):
    task = _seed_task(
        db_session,
        in_inbox=False,
        archived_from_inbox=True,
        status=TaskStatus.ARCHIVED,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc),
    )

    task_mutations.restore_inbox_item(task)

    assert task.in_inbox is True
    assert task.archived_from_inbox is False
    assert task.status == TaskStatus.PENDING
    assert task.intake_container == INBOX_INTENT_UNPROCESSED
    assert task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert task.intake_processed_at is None
