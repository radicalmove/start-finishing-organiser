from app.models import (
    Project,
    Task,
    TaskStatus,
    WhenBucket,
    INBOX_INTENT_LEARN_EXPLORE,
    INBOX_INTENT_SUPPORT_PROJECT,
)


def test_guided_capture_requires_displacement_ack(client, api_headers):
    res = client.post(
        "/capture/wizard",
        data={"capture_text": "New task"},
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "Confirm+the+displacement+check+before+saving." in res.headers["location"]


def test_guided_capture_requires_title(client, api_headers):
    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "   ",
            "item_kind": "task",
            "displacement_ack": "yes",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "Title+is+required." in res.headers["location"]


def test_guided_capture_creates_task(client, api_headers, db_session):
    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Guided task",
            "item_kind": "task",
            "displacement_ack": "yes",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    task = db_session.query(Task).filter(Task.verb_noun == "Guided task").one()
    assert task.in_inbox is False


def test_guided_capture_creates_project(client, api_headers, db_session):
    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Launch guided project",
            "item_kind": "project",
            "displacement_ack": "true",
            "target_date": "2030-01-10",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    project = db_session.query(Project).filter(Project.title == "Launch guided project").one()
    assert project.active_this_week is True


def test_guided_capture_project_keeps_year_horizon(client, api_headers, db_session):
    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Plan annual roadmap",
            "item_kind": "project",
            "horizon": "year",
            "include_this_week": "no",
            "displacement_ack": "true",
            "target_date": "2031-03-01",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    project = db_session.query(Project).filter(Project.title == "Plan annual roadmap").one()
    assert project.time_horizon == "year"
    assert project.active_this_week is False


def test_guided_capture_project_requires_target_date(client, api_headers):
    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Publish launch plan",
            "item_kind": "project",
            "displacement_ack": "true",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "Set+a+target+date+for+this+project" in res.headers["location"]


def test_guided_capture_project_requires_action_title_without_ack(client, api_headers):
    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Website redesign",
            "item_kind": "project",
            "displacement_ack": "true",
            "target_date": "2030-02-10",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "Project+title+should+start+with+an+action+verb" in res.headers["location"]


def test_guided_capture_task_year_horizon_maps_to_later_bucket(client, api_headers, db_session):
    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Year task",
            "item_kind": "task",
            "horizon": "year",
            "displacement_ack": "yes",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    task = db_session.query(Task).filter(Task.verb_noun == "Year task").one()
    assert task.when_bucket == WhenBucket.LATER


def test_guided_capture_requires_intent_when_processing_source_task(client, api_headers, db_session):
    source = Task(
        verb_noun="Inbox source",
        in_inbox=True,
        status=TaskStatus.PENDING,
        when_bucket=WhenBucket.LATER,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Inbox source",
            "source_task_id": str(source.id),
            "item_kind": "task",
            "displacement_ack": "yes",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "Choose+how+to+handle+this+inbox+item+before+saving." in res.headers["location"]


def test_guided_capture_routes_source_task_to_learning(client, api_headers, db_session):
    source = Task(
        verb_noun="Inbox source",
        in_inbox=True,
        status=TaskStatus.PENDING,
        when_bucket=WhenBucket.LATER,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Read this later",
            "source_task_id": str(source.id),
            "inbox_intent": INBOX_INTENT_LEARN_EXPLORE,
            "item_kind": "task",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303

    db_session.refresh(source)
    assert source.verb_noun == "Read this later"
    assert source.in_inbox is False
    assert source.status == TaskStatus.PENDING
    assert source.intake_container == INBOX_INTENT_LEARN_EXPLORE


def test_guided_capture_support_project_source_task_requires_project_link(client, api_headers, db_session):
    source = Task(
        verb_noun="Inbox source",
        in_inbox=True,
        status=TaskStatus.PENDING,
        when_bucket=WhenBucket.LATER,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    res = client.post(
        "/capture/wizard",
        data={
            "capture_text": "Action this",
            "source_task_id": str(source.id),
            "inbox_intent": INBOX_INTENT_SUPPORT_PROJECT,
            "item_kind": "task",
            "displacement_ack": "yes",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "Select+an+existing+project+or+choose+Project+flow." in res.headers["location"]
