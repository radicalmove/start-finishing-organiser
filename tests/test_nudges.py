from app.models import GuidanceReminder


def test_nudges_get_is_read_only(client, api_headers, db_session):
    before = db_session.query(GuidanceReminder).count()
    res = client.get("/nudges", headers=api_headers)
    after = db_session.query(GuidanceReminder).count()
    assert res.status_code == 200
    assert before == after


def test_nudges_refresh_populates_reminders(client, api_headers, db_session):
    res = client.post("/nudges/refresh", headers=api_headers)
    assert res.status_code == 200
    assert db_session.query(GuidanceReminder).count() >= 1
