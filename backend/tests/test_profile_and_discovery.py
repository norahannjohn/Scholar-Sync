from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.fixtures.sample_scholarships import seed_test_scholarships


def test_profile_validation_and_optional_fields(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "prof@example.com", "password": "Password1234!"},
    )
    # Invalid percentage > 100 rejected
    bad = client.put(
        "/api/v1/profile",
        json={"grading_scale": "percentage", "academic_score": 105},
    )
    assert bad.status_code == 422

    # Valid partial profile without sensitive fields works
    ok = client.put(
        "/api/v1/profile",
        json={
            "state_ut": "Karnataka",
            "education_level": "undergraduate",
            "course_field": "Computer Science Engineering",
            "gender": "prefer_not_to_say",
        },
    )
    assert ok.status_code == 200
    data = ok.json()
    assert data["state_ut"] == "Karnataka"
    assert data["annual_family_income_inr"] is None
    assert data["completeness_fields_filled"] >= 3


def test_discovery_search_filters_sorting_and_pagination(
    client: TestClient, db_session: Session
) -> None:
    seed_test_scholarships(db_session)

    r_all = client.get("/api/v1/scholarships?page=1&page_size=1")
    assert r_all.status_code == 200
    body = r_all.json()
    assert body["total"] == 2
    assert body["total_pages"] == 2
    assert len(body["items"]) == 1

    r_search = client.get("/api/v1/scholarships?q=North%20East")
    assert r_search.status_code == 200
    assert r_search.json()["total"] == 1
    assert r_search.json()["items"][0]["slug"] == "test-fixture-ner-merit"

    r_state = client.get("/api/v1/scholarships?state_ut=Assam&sort=deadline")
    assert r_state.status_code == 200
    assert r_state.json()["total"] == 2  # All India + Assam
