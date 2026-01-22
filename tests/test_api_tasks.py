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
    assert any(row["id"] == task["id"] for row in res.json())

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
