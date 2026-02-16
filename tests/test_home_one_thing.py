import re


def _set_one_thing(client, api_headers, title: str):
    response = client.post(
        "/coach/message",
        headers=api_headers,
        json={
            "message": f"set my one thing to {title}",
            "screen_context": {"screen": {"id": "home"}},
        },
    )
    assert response.status_code == 200


def test_home_header_now_uses_one_thing_when_no_active_block(client, api_headers):
    _set_one_thing(client, api_headers, "Finish proposal draft")

    response = client.get("/")
    assert response.status_code == 200
    assert re.search(r"data-now-text>\s*Finish proposal draft\s*</span>", response.text)


def test_home_no_block_copy_reflects_one_thing_after_coach_update(client, api_headers):
    _set_one_thing(client, api_headers, "Finish proposal draft")

    response = client.get("/")
    assert response.status_code == 200
    assert "No block active right now. One Thing is set. Pick a Frog and protect a block." in response.text
