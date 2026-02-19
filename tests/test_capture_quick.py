from app.models import Project, Task


def test_quick_capture_requires_title(client, api_headers):
    res = client.post(
        "/capture",
        data={"title": "   "},
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"].startswith("/capture?error=Title+is+required")


def test_quick_capture_not_sure_redirects_to_wizard(client, api_headers):
    res = client.post(
        "/capture",
        data={"title": "Plan trip", "capture_kind": "not_sure"},
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/capture/wizard?prefill=Plan+trip"


def test_quick_capture_decide_later_creates_inbox_task(client, api_headers, db_session):
    res = client.post(
        "/capture",
        data={"title": "Inbox item", "capture_kind": "decide_later"},
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    task = db_session.query(Task).filter(Task.verb_noun == "Inbox item").one()
    assert task.in_inbox is True


def test_quick_capture_task_sets_resurface_for_future_bucket(client, api_headers, db_session):
    res = client.post(
        "/capture",
        data={
            "title": "Future task",
            "capture_kind": "task",
            "displacement_ack": "yes",
            "task_when_bucket": "month",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    task = db_session.query(Task).filter(Task.verb_noun == "Future task").one()
    assert task.resurface_on is not None


def test_quick_capture_project_keeps_year_horizon(client, api_headers, db_session):
    res = client.post(
        "/capture",
        data={
            "title": "Annual project",
            "capture_kind": "project",
            "displacement_ack": "yes",
            "project_time_horizon": "year",
            "project_include_this_week": "no",
        },
        headers=api_headers,
        follow_redirects=False,
    )
    assert res.status_code == 303
    project = db_session.query(Project).filter(Project.title == "Annual project").one()
    assert project.time_horizon == "year"
