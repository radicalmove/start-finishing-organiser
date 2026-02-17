import io
import json
import zipfile

from app.models import HealthExerciseSession


def test_add_exercise_session_persists_and_renders(client, api_headers, db_session):
    res = client.post(
        "/health/exercise/sessions",
        headers=api_headers,
        data={
            "day_of_week": "monday",
            "focus_area": "strength",
            "title": "Upper body circuit",
            "start_time": "07:30",
            "duration_minutes": "45",
            "notes": "Keep rest under 90 seconds.",
            "return_to": "/health/exercise",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers.get("location") == "/health/exercise"

    session = db_session.query(HealthExerciseSession).first()
    assert session is not None
    assert session.day_of_week == "monday"
    assert session.focus_area == "strength"
    assert session.title == "Upper body circuit"
    assert session.duration_minutes == 45
    assert session.is_active is True

    page = client.get("/health/exercise", headers=api_headers)
    assert page.status_code == 200
    assert "Upper body circuit" in page.text
    assert "/health/strength" in page.text


def test_deactivate_exercise_session_moves_to_recently_removed(client, api_headers, db_session):
    session = HealthExerciseSession(
        day_of_week="wednesday",
        focus_area="fitness",
        title="Zone 2 run",
        duration_minutes=35,
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    res = client.post(
        "/health/exercise/sessions/deactivate",
        headers=api_headers,
        data={"session_id": str(session.id), "return_to": "/health/exercise"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers.get("location") == "/health/exercise"

    db_session.refresh(session)
    assert session.is_active is False

    page = client.get("/health/exercise", headers=api_headers)
    assert page.status_code == 200
    assert "Recently removed" in page.text
    assert "Zone 2 run" in page.text


def test_add_exercise_session_requires_title(client, api_headers):
    res = client.post(
        "/health/exercise/sessions",
        headers=api_headers,
        data={
            "day_of_week": "friday",
            "focus_area": "flexibility",
            "title": "   ",
            "return_to": "/health/exercise",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "error=Session+title+is+required." in (res.headers.get("location") or "")


def test_health_nav_shows_exercise_plan_tab(client, api_headers):
    page = client.get("/health", headers=api_headers)
    assert page.status_code == 200
    assert "href=\"/health/exercise\"" in page.text


def test_export_health_includes_exercise_sessions(client, api_headers):
    client.post(
        "/health/exercise/sessions",
        headers=api_headers,
        data={
            "day_of_week": "saturday",
            "focus_area": "flexibility",
            "title": "Hip mobility flow",
            "duration_minutes": "20",
            "return_to": "/health/exercise",
        },
        follow_redirects=False,
    )

    res = client.post(
        "/export",
        headers=api_headers,
        data={
            "range_choice": "all",
            "include_health": "on",
        },
    )
    assert res.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(res.content))
    assert "health_exercise_sessions.json" in set(archive.namelist())
    payload = json.loads(archive.read("health_exercise_sessions.json").decode("utf-8"))
    assert any(row.get("title") == "Hip mobility flow" for row in payload)
