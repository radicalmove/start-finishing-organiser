from app.models import Task, TaskStatus, WhenBucket


def test_inbox_update_and_archive_flow(client, api_headers, db_session):
    task = Task(
        verb_noun="Review inbox item",
        description="Old description",
        in_inbox=True,
        when_bucket=WhenBucket.LATER,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    update = client.post(
        "/inbox/update",
        headers={**api_headers, "accept": "application/json"},
        data={"task_id": str(task.id), "description": "  Updated description  "},
    )
    assert update.status_code == 200
    update_payload = update.json()
    assert update_payload["ok"] is True
    assert update_payload["description"] == "Updated description"

    db_session.refresh(task)
    assert task.description == "Updated description"
    assert task.in_inbox is True
    assert task.status == TaskStatus.PENDING

    archive = client.post(
        "/inbox/archive",
        headers={**api_headers, "accept": "application/json"},
        data={"task_id": str(task.id)},
    )
    assert archive.status_code == 200
    archive_payload = archive.json()
    assert archive_payload["ok"] is True
    assert archive_payload["removed"] is True

    db_session.refresh(task)
    assert task.in_inbox is False
    assert task.archived_from_inbox is True
    assert task.status == TaskStatus.ARCHIVED
