def test_health_trackers_hub_renders_with_category_links(client, api_headers):
    page = client.get("/health/trackers", headers=api_headers)
    assert page.status_code == 200
    assert "Tracker areas" in page.text
    assert "href=\"/health/diet\"" in page.text
    assert "href=\"/health/weight\"" in page.text
    assert "href=\"/health/fitness\"" in page.text
    assert "href=\"/health/strength\"" in page.text
    assert "href=\"/health/flexibility\"" in page.text


def test_health_detail_pages_show_tracker_subnav(client, api_headers):
    page = client.get("/health/diet", headers=api_headers)
    assert page.status_code == 200
    assert "href=\"/health/trackers\"" in page.text
    assert "href=\"/health/fitness\"" in page.text
    assert "href=\"/health/strength\"" in page.text
