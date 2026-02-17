import pytest


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


@pytest.mark.parametrize(
    "path",
    [
        "/tasks/time",
        "/inbox/containers?tab=learning",
        "/health/training",
    ],
)
def test_primary_views_keep_skip_link_and_main_landmark(client, api_headers, path):
    response = client.get(path, headers=api_headers)
    assert response.status_code == 200
    html = response.text
    assert 'class="skip-link" href="#main-content"' in html
    assert 'id="main-content"' in html


def test_recycle_bin_confirm_modal_is_accessible(client, api_headers):
    response = client.get("/inbox/containers?tab=recycle", headers=api_headers)
    assert response.status_code == 200
    html = response.text
    assert 'id="recycle-empty-modal"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'aria-labelledby="recycle-empty-title"' in html


def test_training_live_tools_expose_button_labels(client, api_headers):
    response = client.get("/health/training", headers=api_headers)
    assert response.status_code == 200
    html = response.text
    assert "Quick counter" in html
    assert "Rest timer" in html
    assert "data-counter-add-set" in html
    assert "data-counter-add-rep" in html
    assert "data-rest-start" in html
