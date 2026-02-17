from datetime import datetime, timezone, timedelta

from app.models import Task, TaskStatus, WhenBucket


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
