from app.models import Project, ProjectCategory


def test_onboarding_project_seed_is_idempotent(client, api_headers, db_session):
    payload = {
        "name": "Solo User",
        "work_projects": "Alpha\nAlpha\nBeta",
        "personal_projects": "Health\nHealth",
    }
    first = client.post("/onboarding", data=payload, headers=api_headers, follow_redirects=False)
    second = client.post("/onboarding", data=payload, headers=api_headers, follow_redirects=False)

    assert first.status_code == 303
    assert second.status_code == 303
    assert (
        db_session.query(Project)
        .filter(Project.category == ProjectCategory.WORK, Project.title == "Alpha")
        .count()
        == 1
    )
    assert (
        db_session.query(Project)
        .filter(Project.category == ProjectCategory.WORK, Project.title == "Beta")
        .count()
        == 1
    )
    assert (
        db_session.query(Project)
        .filter(Project.category == ProjectCategory.PERSONAL, Project.title == "Health")
        .count()
        == 1
    )
