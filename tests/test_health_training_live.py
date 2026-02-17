import io
import json
import zipfile

from app.models import HealthExerciseSession, HealthTrainingPlan, HealthTrainingSetLog


def test_health_training_page_renders(client, api_headers):
    page = client.get("/health/training", headers=api_headers)
    assert page.status_code == 200
    assert "Training live" in page.text
    assert "Edit weekly plan" in page.text
    assert "Add context (optional)" in page.text
    assert "Create overall plan" in page.text


def test_save_training_plan_sets_active_plan(client, api_headers, db_session):
    res = client.post(
        "/health/training/plans",
        headers=api_headers,
        data={
            "title": "10-week strength base",
            "start_date": "2026-02-16",
            "end_date": "2026-04-26",
            "focus_goal": "Build squat and pull-up volume",
            "notes": "Deload every 4th week.",
            "return_to": "/health/training",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers.get("location") == "/health/training"

    plan = db_session.query(HealthTrainingPlan).filter(HealthTrainingPlan.is_active.is_(True)).first()
    assert plan is not None
    assert plan.title == "10-week strength base"

    page = client.get("/health/training", headers=api_headers)
    assert page.status_code == 200
    assert "10-week strength base" in page.text


def test_log_training_set_for_today(client, api_headers, db_session):
    session = HealthExerciseSession(
        day_of_week="monday",
        focus_area="strength",
        title="Lower body strength",
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    res = client.post(
        "/health/training/sets",
        headers=api_headers,
        data={
            "session_id": str(session.id),
            "exercise_name": "Front squat",
            "reps": "6",
            "load_text": "70 kg",
            "duration_seconds": "",
            "notes": "RPE 8",
            "return_to": "/health/training",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers.get("location") == "/health/training"

    log = db_session.query(HealthTrainingSetLog).first()
    assert log is not None
    assert log.reps == 6
    assert log.exercise_name == "Front squat"
    assert log.session_id == session.id

    page = client.get("/health/training", headers=api_headers)
    assert page.status_code == 200
    assert "Front squat" in page.text
    assert "6 reps" in page.text


def test_training_export_contains_plans_and_logs(client, api_headers):
    client.post(
        "/health/training/plans",
        headers=api_headers,
        data={
            "title": "Engine block",
            "return_to": "/health/training",
        },
        follow_redirects=False,
    )
    client.post(
        "/health/training/sets",
        headers=api_headers,
        data={
            "exercise_name": "Bike intervals",
            "duration_seconds": "90",
            "return_to": "/health/training",
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
    names = set(archive.namelist())
    assert "health_training_plans.json" in names
    assert "health_training_set_logs.json" in names

    plans = json.loads(archive.read("health_training_plans.json").decode("utf-8"))
    logs = json.loads(archive.read("health_training_set_logs.json").decode("utf-8"))
    assert any(row.get("title") == "Engine block" for row in plans)
    assert any(row.get("exercise_name") == "Bike intervals" for row in logs)
