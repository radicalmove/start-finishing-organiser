def test_api_projects_requires_token(client):
    res = client.get("/api/projects")
    assert res.status_code == 401


def test_api_projects_crud(client, api_headers):
    payload = {
        "title": "Test Project",
        "description": "Scope",
        "category": "work",
        "active_this_week": False,
    }
    res = client.post("/api/projects", json=payload, headers=api_headers)
    assert res.status_code == 201
    project = res.json()
    assert project["title"] == "Test Project"

    res = client.get("/api/projects", headers=api_headers)
    assert res.status_code == 200
    assert any(row["id"] == project["id"] for row in res.json())

    res = client.patch(
        f"/api/projects/{project['id']}",
        json={"title": "Updated Project"},
        headers=api_headers,
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Project"

    res = client.delete(f"/api/projects/{project['id']}", headers=api_headers)
    assert res.status_code == 204


def test_api_projects_weekly_cap(client, api_headers):
    for idx in range(4):
        res = client.post(
            "/api/projects",
            json={
                "title": f"Work {idx}",
                "category": "work",
                "active_this_week": True,
            },
            headers=api_headers,
        )
        assert res.status_code == 201

    res = client.post(
        "/api/projects",
        json={
            "title": "Work 5",
            "category": "work",
            "active_this_week": True,
        },
        headers=api_headers,
    )
    assert res.status_code == 400
    assert "Weekly cap" in res.json()["detail"]
