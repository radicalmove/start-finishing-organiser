from app.models import HealthSupplement


def test_add_health_supplement_persists_and_renders(client, api_headers, db_session):
    res = client.post(
        "/health/supplements",
        headers=api_headers,
        data={
            "name": "Magnesium glycinate",
            "dose": "300 mg",
            "timing": "bedtime",
            "timing_detail": "30 minutes before sleep",
            "notes": "Helps wind down",
            "return_to": "/health/supplements",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers.get("location") == "/health/supplements"

    supplement = db_session.query(HealthSupplement).first()
    assert supplement is not None
    assert supplement.name == "Magnesium glycinate"
    assert supplement.dose == "300 mg"
    assert supplement.timing == "bedtime"
    assert supplement.timing_detail == "30 minutes before sleep"
    assert supplement.notes == "Helps wind down"
    assert supplement.is_active is True

    page = client.get("/health/supplements", headers=api_headers)
    assert page.status_code == 200
    assert "Magnesium glycinate" in page.text
    assert "300 mg" in page.text


def test_deactivate_health_supplement_moves_to_recently_stopped(client, api_headers, db_session):
    supplement = HealthSupplement(
        name="Vitamin D3",
        dose="1000 IU",
        timing="morning",
        is_active=True,
    )
    db_session.add(supplement)
    db_session.commit()
    db_session.refresh(supplement)

    res = client.post(
        "/health/supplements/deactivate",
        headers=api_headers,
        data={"supplement_id": str(supplement.id), "return_to": "/health/supplements"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers.get("location") == "/health/supplements"

    db_session.refresh(supplement)
    assert supplement.is_active is False

    page = client.get("/health/supplements", headers=api_headers)
    assert page.status_code == 200
    assert "Recently stopped" in page.text
    assert "Vitamin D3" in page.text


def test_add_health_supplement_requires_name(client, api_headers):
    res = client.post(
        "/health/supplements",
        headers=api_headers,
        data={
            "name": "   ",
            "timing": "morning",
            "return_to": "/health/supplements",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "error=Supplement+name+is+required." in (res.headers.get("location") or "")


def test_health_dashboard_no_longer_contains_supplements_panel(client, api_headers):
    page = client.get("/health", headers=api_headers)
    assert page.status_code == 200
    assert "Save supplement" not in page.text
    assert "href=\"/health/supplements\"" in page.text
