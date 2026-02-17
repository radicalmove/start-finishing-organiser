def test_api_tasks_crud(client, api_headers):
    payload = {
        "verb_noun": "Draft test plan",
        "in_inbox": False,
        "when_bucket": "today",
    }
    res = client.post("/api/tasks", json=payload, headers=api_headers)
    assert res.status_code == 201
    task = res.json()
    assert task["verb_noun"] == "Draft test plan"

    res = client.get("/api/tasks", headers=api_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(row["id"] == task["id"] for row in body["items"])

    res = client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "done", "frog": True},
        headers=api_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "done"
    assert res.json()["frog"] is True

    res = client.delete(f"/api/tasks/{task['id']}", headers=api_headers)
    assert res.status_code == 204


def test_api_tasks_pagination(client, api_headers):
    for idx in range(5):
        res = client.post(
            "/api/tasks",
            json={
                "verb_noun": f"Task {idx}",
                "in_inbox": False,
                "when_bucket": "week",
            },
            headers=api_headers,
        )
        assert res.status_code == 201

    page_one = client.get("/api/tasks?page=1&page_size=2", headers=api_headers)
    assert page_one.status_code == 200
    body_one = page_one.json()
    assert body_one["page"] == 1
    assert body_one["page_size"] == 2
    assert body_one["total"] >= 5
    assert body_one["total_pages"] >= 3
    assert len(body_one["items"]) == 2

    page_two = client.get("/api/tasks?page=2&page_size=2", headers=api_headers)
    assert page_two.status_code == 200
    body_two = page_two.json()
    assert body_two["page"] == 2
    assert len(body_two["items"]) == 2
