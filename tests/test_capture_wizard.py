from app.models import Project, Task


def test_guided_capture_requires_displacement_ack(client, api_headers):
    res = client.post(
        "/capture/wizard",
        data={"capture_text": "New task"},
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "Confirm+the+displacement+check+before+saving." in res.headers["location"]


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
            "capture_text": "Guided project",
            "item_kind": "project",
            "displacement_ack": "true",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    project = db_session.query(Project).filter(Project.title == "Guided project").one()
    assert project.active_this_week is True
