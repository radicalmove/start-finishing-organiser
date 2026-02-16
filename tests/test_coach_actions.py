import json
from datetime import date

from app.routes import coach
from app.models import CoachMessage, RitualEntry, RitualType


def test_parse_one_thing_action_matches_plain_english():
    parsed = coach._parse_one_thing_action("set my one thing to Finish proposal draft")
    assert parsed == "Finish proposal draft"


def test_parse_task_action_extracts_title_and_bucket():
    action = coach._parse_task_action("add task draft launch email this week")
    assert action is not None
    assert action["title"] == "draft launch email"
    assert action["in_inbox"] is False
    assert action["when_bucket"].value == "week"


def test_parse_time_block_action_parses_range_and_title():
    action = coach._parse_time_block_action("schedule a focus block from 3pm to 4pm for Deep work")
    assert action is not None
    assert action["title"] == "Deep work"
    assert action["start_time"].hour == 15
    assert action["end_time"].hour == 16


def test_coach_message_sets_one_thing_and_returns_effects(client, api_headers, db_session):
    response = client.post(
        "/coach/message",
        headers=api_headers,
        json={
            "message": "set my one thing to Finish proposal draft",
            "screen_context": {"screen": {"id": "home"}},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["engine"] == "action"
    assert payload["effects"]["type"] == "one_thing_updated"
    assert payload["effects"]["one_thing"] == "Finish proposal draft"

    entry = (
        db_session.query(RitualEntry)
        .filter(
            RitualEntry.entry_date == date.today(),
            RitualEntry.ritual_type == RitualType.MORNING,
        )
        .first()
    )
    assert entry is not None
    assert entry.one_thing == "Finish proposal draft"


def test_coach_message_compacts_context_before_storage(client, api_headers, db_session):
    context = {
        "screen": {"id": "home", "title": "Home", "path": "/"},
        "generated_at": "2026-02-16T00:00:00",
        "screen_data": {
            "inbox_tasks": [{"id": i, "verb_noun": f"item {i}"} for i in range(1, 10)],
        },
        "lists": {
            "profile": {"name": "R"},
            "tasks": [{"id": i, "verb_noun": f"task {i}"} for i in range(1, 20)],
            "projects": [{"id": i, "title": f"project {i}"} for i in range(1, 12)],
        },
    }
    response = client.post(
        "/coach/message",
        headers=api_headers,
        json={
            "message": "set my one thing to Tight context storage",
            "screen_context": context,
        },
    )
    assert response.status_code == 200

    stored = (
        db_session.query(CoachMessage)
        .filter(CoachMessage.role == "user")
        .order_by(CoachMessage.id.desc())
        .first()
    )
    assert stored is not None
    assert stored.context_json is not None
    payload = json.loads(stored.context_json)
    assert len(payload["screen_data"]["inbox_tasks"]) <= 4
    assert len(payload["lists"]["tasks"]) <= 6
    assert len(payload["lists"]["projects"]) <= 6
