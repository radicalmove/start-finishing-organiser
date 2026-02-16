def test_home_includes_skip_link_and_landmark(client, api_headers):
    response = client.get("/", headers=api_headers)
    assert response.status_code == 200
    html = response.text
    assert 'class="skip-link" href="#main-content"' in html
    assert 'id="main-content"' in html


def test_home_coach_regions_include_live_announcements(client, api_headers):
    response = client.get("/", headers=api_headers)
    assert response.status_code == 200
    html = response.text
    assert "data-coach-status" in html
    assert 'role="status"' in html
    assert "data-coach-messages" in html
    assert 'role="log"' in html
    assert 'aria-live="polite"' in html
