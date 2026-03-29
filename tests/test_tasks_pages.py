from datetime import datetime, timezone, timedelta

from app.models import (
    BlockType,
    INBOX_INTENT_UNPROCESSED,
    Project,
    Task,
    TaskStatus,
    WhenBucket,
)


def _seed_tasks(db_session, *, status: TaskStatus, count: int, prefix: str) -> None:
    now = datetime.now(timezone.utc)
    tasks = []
    for idx in range(count):
        task = Task(
            verb_noun=f"{prefix} {idx}",
            status=status,
            when_bucket=WhenBucket.LATER,
            in_inbox=False,
            archived_from_inbox=(status == TaskStatus.ARCHIVED),
            completed_at=now - timedelta(minutes=idx) if status == TaskStatus.DONE else None,
        )
        tasks.append(task)
    db_session.add_all(tasks)
    db_session.commit()


def _seed_task(db_session, **kwargs) -> Task:
    task = Task(
        verb_noun="Lifecycle task",
        when_bucket=WhenBucket.LATER,
        **kwargs,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_completed_tasks_page_pagination(client, api_headers, db_session):
    _seed_tasks(db_session, status=TaskStatus.DONE, count=45, prefix="Completed task")

    page_one = client.get("/tasks/completed?completed_page=1", headers=api_headers)
    assert page_one.status_code == 200
    assert "Page 1 of 2" in page_one.text
    assert "/tasks/completed?completed_page=2" in page_one.text

    page_two = client.get("/tasks/completed?completed_page=2", headers=api_headers)
    assert page_two.status_code == 200
    assert "Page 2 of 2" in page_two.text
    assert "/tasks/completed?completed_page=1" in page_two.text


def test_archived_tasks_page_pagination(client, api_headers, db_session):
    _seed_tasks(db_session, status=TaskStatus.ARCHIVED, count=42, prefix="Archived task")

    page_one = client.get("/tasks/archived?archived_page=1", headers=api_headers)
    assert page_one.status_code == 200
    assert "Page 1 of 2" in page_one.text
    assert "/tasks/archived?archived_page=2" in page_one.text

    page_two = client.get("/tasks/archived?archived_page=2", headers=api_headers)
    assert page_two.status_code == 200
    assert "Page 2 of 2" in page_two.text
    assert "/tasks/archived?archived_page=1" in page_two.text


def test_create_task_route_normalizes_form_input(client, api_headers, db_session):
    project = Project(title="Project A")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    create_res = client.post(
        "/tasks/form",
        headers=api_headers,
        data={
            "verb_noun": "  Draft plan  ",
            "description": "  Outline next steps  ",
            "project_id": str(project.id),
            "when_bucket": WhenBucket.TODAY.value,
            "block_type": BlockType.FOCUS.value,
            "duration_minutes": "45",
            "frog": "true",
        },
        follow_redirects=False,
    )
    assert create_res.status_code == 303

    task = db_session.query(Task).one()
    assert task.verb_noun == "Draft plan"
    assert task.description == "Outline next steps"
    assert task.project_id == project.id
    assert task.when_bucket == WhenBucket.TODAY
    assert task.block_type == BlockType.FOCUS
    assert task.duration_minutes == 45
    assert task.frog is True
    assert task.in_inbox is False


def test_complete_task_route_sets_done_and_clears_inbox(client, api_headers, db_session):
    task = _seed_task(db_session, status=TaskStatus.PENDING, in_inbox=True)

    complete_res = client.post(
        "/tasks/complete",
        headers=api_headers,
        data={"task_id": str(task.id)},
        follow_redirects=False,
    )
    assert complete_res.status_code == 303
    db_session.refresh(task)
    assert task.status == TaskStatus.DONE
    assert task.in_inbox is False
    assert task.completed_at is not None


def test_reopen_task_route_clears_completed_at(client, api_headers, db_session):
    task = _seed_task(
        db_session,
        status=TaskStatus.DONE,
        in_inbox=False,
        completed_at=datetime.now(timezone.utc),
    )

    reopen_res = client.post(
        "/tasks/reopen",
        headers=api_headers,
        data={"task_id": str(task.id)},
        follow_redirects=False,
    )
    assert reopen_res.status_code == 303
    db_session.refresh(task)
    assert task.status == TaskStatus.PENDING
    assert task.completed_at is None


def test_archive_task_route_clears_recycle_flag(client, api_headers, db_session):
    task = _seed_task(
        db_session,
        status=TaskStatus.PENDING,
        in_inbox=True,
        archived_from_inbox=True,
    )

    archive_res = client.post(
        "/tasks/archive",
        headers=api_headers,
        data={"task_id": str(task.id)},
        follow_redirects=False,
    )
    assert archive_res.status_code == 303
    db_session.refresh(task)
    assert task.status == TaskStatus.ARCHIVED
    assert task.in_inbox is False
    assert task.archived_from_inbox is False


def test_restore_task_route_returns_recycle_bin_item_to_inbox(client, api_headers, db_session):
    recycle_task = _seed_task(
        db_session,
        status=TaskStatus.ARCHIVED,
        in_inbox=False,
        archived_from_inbox=True,
        intake_container="learn_explore",
        intake_intent="learn_explore",
        intake_processed_at=datetime.now(timezone.utc),
    )

    restore_res = client.post(
        "/tasks/restore",
        headers=api_headers,
        data={"task_id": str(recycle_task.id)},
        follow_redirects=False,
    )
    assert restore_res.status_code == 303
    db_session.refresh(recycle_task)
    assert recycle_task.status == TaskStatus.PENDING
    assert recycle_task.in_inbox is True
    assert recycle_task.completed_at is None
    assert recycle_task.archived_from_inbox is False
    assert recycle_task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert recycle_task.intake_container == INBOX_INTENT_UNPROCESSED
    assert recycle_task.intake_processed_at is None


def test_restore_task_route_keeps_non_recycle_task_out_of_inbox(client, api_headers, db_session):
    archived_task = _seed_task(
        db_session,
        status=TaskStatus.ARCHIVED,
        in_inbox=False,
        archived_from_inbox=False,
    )

    restore_plain_res = client.post(
        "/tasks/restore",
        headers=api_headers,
        data={"task_id": str(archived_task.id)},
        follow_redirects=False,
    )
    assert restore_plain_res.status_code == 303
    db_session.refresh(archived_task)
    assert archived_task.status == TaskStatus.PENDING
    assert archived_task.in_inbox is False
    assert archived_task.completed_at is None
