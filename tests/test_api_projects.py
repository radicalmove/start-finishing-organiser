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
    body = res.json()
    assert body["total"] >= 1
    assert any(row["id"] == project["id"] for row in body["items"])

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


def test_api_projects_pagination(client, api_headers):
    for idx in range(6):
        res = client.post(
            "/api/projects",
            json={
                "title": f"Paged Project {idx}",
                "category": "work",
                "active_this_week": False,
            },
            headers=api_headers,
        )
        assert res.status_code == 201

    page_one = client.get("/api/projects?page=1&page_size=2", headers=api_headers)
    assert page_one.status_code == 200
    body_one = page_one.json()
    assert body_one["page"] == 1
    assert body_one["page_size"] == 2
    assert body_one["total"] >= 6
    assert body_one["total_pages"] >= 3
    assert len(body_one["items"]) == 2

    page_two = client.get("/api/projects?page=2&page_size=2", headers=api_headers)
    assert page_two.status_code == 200
    body_two = page_two.json()
    assert body_two["page"] == 2
    assert len(body_two["items"]) == 2
