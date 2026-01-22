from app.models import Task


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
