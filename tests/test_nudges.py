from datetime import date, datetime, timezone

from app.routes import nudges as nudges_route
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


def test_nudges_refresh_handles_naive_last_shown_at(client, api_headers, db_session, monkeypatch):
    monkeypatch.setattr(
        nudges_route,
        "_pattern_candidates",
        lambda db, today: [
            {
                "code": "pattern_naive_dt",
                "title": "Pattern naive datetime test",
                "body": "Regression coverage.",
                "cooldown_hours": 24,
            }
        ],
    )
    db_session.add(
        GuidanceReminder(
            code="pattern_naive_dt",
            title="Pattern naive datetime test",
            body="Regression coverage.",
            period_start=date.today(),
            due_on=date.today(),
            last_shown_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    db_session.commit()

    res = client.post("/nudges/refresh", headers=api_headers)
    assert res.status_code == 200
