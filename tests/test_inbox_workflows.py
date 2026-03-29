from datetime import datetime, timedelta, timezone

from app.models import (
    Task,
    TaskStatus,
    WhenBucket,
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_PARK_LET_GO,
    INBOX_INTENT_UNPROCESSED,
)


def test_inbox_update_trims_description(client, api_headers, db_session):
    task = Task(
        verb_noun="Review inbox item",
        description="Old description",
        in_inbox=True,
        when_bucket=WhenBucket.LATER,
        status=TaskStatus.PENDING,
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc),
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


def test_inbox_archive_resets_processed_state(client, api_headers, db_session):
    task = Task(
        verb_noun="Review inbox item",
        description="Old description",
        in_inbox=True,
        when_bucket=WhenBucket.LATER,
        status=TaskStatus.PENDING,
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    archive = client.post(
        "/inbox/archive",
        headers={**api_headers, "accept": "application/json"},
        data={"task_id": str(task.id)},
    )
    assert archive.status_code == 200
    archive_payload = archive.json()
    assert archive_payload["ok"] is True
    assert archive_payload["removed"] is True
    assert "undo_available" not in archive_payload

    db_session.refresh(task)
    assert task.in_inbox is False
    assert task.archived_from_inbox is True
    assert task.status == TaskStatus.ARCHIVED
    assert task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert task.intake_container == INBOX_INTENT_UNPROCESSED
    assert task.intake_processed_at is None
    assert task.completed_at is not None


def test_inbox_route_and_undo_flow(client, api_headers, db_session):
    task = Task(
        verb_noun="Learn this",
        in_inbox=True,
        when_bucket=WhenBucket.LATER,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    route_res = client.post(
        "/inbox/route",
        headers={**api_headers, "accept": "application/json"},
        data={"task_id": str(task.id), "intent": INBOX_INTENT_LEARN_EXPLORE},
    )
    assert route_res.status_code == 200
    route_payload = route_res.json()
    assert route_payload["ok"] is True
    assert route_payload["removed"] is True
    assert route_payload["undo_available"] is True

    db_session.refresh(task)
    assert task.in_inbox is False
    assert task.status == TaskStatus.PENDING
    assert task.intake_container == INBOX_INTENT_LEARN_EXPLORE

    undo_res = client.post(
        "/inbox/undo",
        headers={**api_headers, "accept": "application/json"},
        data={"task_id": str(task.id)},
    )
    assert undo_res.status_code == 200
    undo_payload = undo_res.json()
    assert undo_payload["ok"] is True
    assert undo_payload["restored"] is True

    db_session.refresh(task)
    assert task.in_inbox is True
    assert task.status == TaskStatus.PENDING
    assert task.archived_from_inbox is False
    assert task.intake_intent == INBOX_INTENT_UNPROCESSED
    assert task.intake_container == INBOX_INTENT_UNPROCESSED
    assert task.intake_processed_at is None


def test_inbox_metrics_reports_age_and_processed_counts(client, api_headers, db_session):
    old_inbox = Task(
        verb_noun="Old inbox",
        in_inbox=True,
        status=TaskStatus.PENDING,
        when_bucket=WhenBucket.LATER,
        intake_container=INBOX_INTENT_UNPROCESSED,
        created_at=datetime.now(timezone.utc) - timedelta(days=20),
    )
    fresh_inbox = Task(
        verb_noun="Fresh inbox",
        in_inbox=True,
        status=TaskStatus.PENDING,
        when_bucket=WhenBucket.LATER,
        intake_container=INBOX_INTENT_UNPROCESSED,
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    processed_learning = Task(
        verb_noun="Learning item",
        in_inbox=False,
        status=TaskStatus.PENDING,
        when_bucket=WhenBucket.LATER,
        intake_intent=INBOX_INTENT_LEARN_EXPLORE,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
        intake_processed_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add_all([old_inbox, fresh_inbox, processed_learning])
    db_session.commit()

    res = client.get("/inbox/metrics", headers={**api_headers, "accept": "application/json"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["inbox_total"] == 2
    assert payload["inbox_older_than_14_days"] == 1
    assert payload["unprocessed_over_7_days"] == 1
    assert payload["processed_last_7_days"].get(INBOX_INTENT_LEARN_EXPLORE) == 1


def test_inbox_route_park_is_not_recycle_bin(client, api_headers, db_session):
    task = Task(
        verb_noun="Park this",
        in_inbox=True,
        when_bucket=WhenBucket.LATER,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    res = client.post(
        "/inbox/route",
        headers={**api_headers, "accept": "application/json"},
        data={"task_id": str(task.id), "intent": INBOX_INTENT_PARK_LET_GO},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["intent"] == INBOX_INTENT_PARK_LET_GO

    db_session.refresh(task)
    assert task.in_inbox is False
    assert task.status == TaskStatus.PENDING
    assert task.archived_from_inbox is False
    assert task.intake_container == INBOX_INTENT_PARK_LET_GO


def test_inbox_containers_page_is_reachable(client, api_headers, db_session):
    learning = Task(
        verb_noun="Learning item",
        in_inbox=False,
        status=TaskStatus.PENDING,
        when_bucket=WhenBucket.LATER,
        intake_container=INBOX_INTENT_LEARN_EXPLORE,
    )
    deleted = Task(
        verb_noun="Deleted item",
        in_inbox=False,
        archived_from_inbox=True,
        status=TaskStatus.ARCHIVED,
        when_bucket=WhenBucket.LATER,
    )
    db_session.add_all([learning, deleted])
    db_session.commit()

    learning_page = client.get("/inbox/containers?tab=learning", headers=api_headers)
    assert learning_page.status_code == 200
    assert "Learning backlog" in learning_page.text
    assert "Learning item" in learning_page.text

    recycle_page = client.get("/inbox/containers?tab=recycle", headers=api_headers)
    assert recycle_page.status_code == 200
    assert "Recycle bin" in recycle_page.text
    assert "Deleted item" in recycle_page.text


def test_empty_recycle_bin_only_deletes_recycle_items(client, api_headers, db_session):
    recycle_one = Task(
        verb_noun="Recycle one",
        in_inbox=False,
        archived_from_inbox=True,
        status=TaskStatus.ARCHIVED,
        when_bucket=WhenBucket.LATER,
    )
    recycle_two = Task(
        verb_noun="Recycle two",
        in_inbox=False,
        archived_from_inbox=True,
        status=TaskStatus.ARCHIVED,
        when_bucket=WhenBucket.LATER,
    )
    normal_archived = Task(
        verb_noun="Normal archived",
        in_inbox=False,
        archived_from_inbox=False,
        status=TaskStatus.ARCHIVED,
        when_bucket=WhenBucket.LATER,
    )
    db_session.add_all([recycle_one, recycle_two, normal_archived])
    db_session.commit()

    res = client.post(
        "/inbox/recycle/empty",
        headers=api_headers,
        data={"next_url": "/inbox/containers?tab=recycle"},
        follow_redirects=False,
    )
    assert res.status_code == 303

    remaining = db_session.query(Task).order_by(Task.id.asc()).all()
    assert len(remaining) == 1
    assert remaining[0].verb_noun == "Normal archived"
    assert remaining[0].archived_from_inbox is False


def test_recycle_bin_cleanup_requires_explicit_action(client, api_headers, db_session, monkeypatch):
    monkeypatch.setenv("SFO_RECYCLE_BIN_RETENTION_DAYS", "30")
    expired_recycle = Task(
        verb_noun="Expired recycle item",
        in_inbox=False,
        archived_from_inbox=True,
        status=TaskStatus.ARCHIVED,
        when_bucket=WhenBucket.LATER,
        completed_at=datetime.now(timezone.utc) - timedelta(days=31),
    )
    fresh_recycle = Task(
        verb_noun="Fresh recycle item",
        in_inbox=False,
        archived_from_inbox=True,
        status=TaskStatus.ARCHIVED,
        when_bucket=WhenBucket.LATER,
        completed_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add_all([expired_recycle, fresh_recycle])
    db_session.commit()

    res = client.get("/inbox/containers?tab=recycle", headers=api_headers)
    assert res.status_code == 200
    assert "Auto-cleanup removes items after 30 days." in res.text
    assert "Fresh recycle item" in res.text
    assert "Expired recycle item" in res.text
    assert "currently exceed the retention window" in res.text

    purge = client.post(
        "/inbox/recycle/purge-expired",
        headers=api_headers,
        data={"next_url": "/inbox/containers?tab=recycle"},
        follow_redirects=False,
    )
    assert purge.status_code == 303

    rows = (
        db_session.query(Task)
        .filter(Task.archived_from_inbox.is_(True), Task.status == TaskStatus.ARCHIVED)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].verb_noun == "Fresh recycle item"
