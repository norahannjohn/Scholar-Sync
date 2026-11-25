from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agent.web_discovery import extract_query_intent, is_safe_official_url
from app.collectors.intl_adapter import parse_month_first_or_day_first
from app.eligibility.engine import evaluate_eligibility
from app.models.scholarship import Scholarship


def test_ssrf_and_official_domain_guard() -> None:
    assert is_safe_official_url("https://cscuk.fcdo.gov.uk/scholarships/") is True
    assert is_safe_official_url("https://www.campusfrance.org/en/eiffel") is True
    assert is_safe_official_url("https://www.aicte.gov.in/schemes") is True
    assert is_safe_official_url("http://127.0.0.1:8000/secret") is False
    assert is_safe_official_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_official_url("file:///etc/passwd") is False
    assert is_safe_official_url("https://random-untrusted-blog.example.com/offer") is False


def test_international_eligibility_and_intent_parsing() -> None:
    intent = extract_query_intent(
        "I am an Indian student looking for fully funded Master's scholarships in UK or France"
    )
    assert intent["study_scope"] == "international_abroad"
    assert "United Kingdom" in intent["destination_countries"]
    assert "France" in intent["destination_countries"]
    assert intent["education_level"] == "postgraduate"
    assert intent["funding_type"] == "full_funding"

    intl_rules = {
        "version": 1,
        "criteria": [
            {
                "key": "nat",
                "label": "Indian nationality",
                "field": "nationality",
                "operator": "in",
                "value": ["India", "Indian"],
                "description": "Indian citizen",
                "mandatory": True,
            },
            {
                "key": "age",
                "label": "Age <= 29",
                "field": "age_years",
                "operator": "max",
                "value": 29,
                "description": "Age up to 29 for Master's",
                "mandatory": True,
            },
        ],
    }
    assert (
        evaluate_eligibility(intl_rules, {"nationality": "India", "age_years": 24}).overall_status
        == "POTENTIAL_MATCH"
    )
    assert (
        evaluate_eligibility(intl_rules, {"nationality": "India", "age_years": 31}).overall_status
        == "NOT_ELIGIBLE"
    )
    assert (
        evaluate_eligibility(intl_rules, {"nationality": "India"}).overall_status
        == "NEEDS_MORE_INFORMATION"
    )


def test_international_date_parser() -> None:
    assert parse_month_first_or_day_first("January 6, 2027") == date(2027, 1, 6)
    assert parse_month_first_or_day_first("23 July 2026") == date(2026, 7, 23)


def test_discover_filter_by_scope_country_and_agent_live_web(
    client: TestClient, db_session: Session
) -> None:
    now = datetime.now(UTC)
    db_session.add(
        Scholarship(
            slug="test-uk-masters",
            name="TEST FIXTURE — UK Master's Fellowship",
            provider="Test UK Council",
            provider_type="foreign_government",
            scholarship_type="merit",
            study_scope="international_abroad",
            destination_countries=["United Kingdom"],
            target_universities=["University of Oxford"],
            eligible_nationalities=["India"],
            funding_type="full_funding",
            description="Test fixture UK full scholarship for Indian students.",
            applicable_states=["All India"],
            education_levels=["postgraduate"],
            courses=["Computer Science"],
            structured_rules={
                "version": 1,
                "criteria": [
                    {
                        "key": "nat",
                        "label": "Indian citizen",
                        "field": "nationality",
                        "operator": "eq",
                        "value": "India",
                        "description": "Indian citizen",
                        "mandatory": True,
                    }
                ],
            },
            required_documents=[],
            application_steps=[],
            status="OPEN",
            official_info_url="https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
            source_type="official_html",
            source_url="https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
            last_checked_at=now,
            last_verified_at=now,
            verification_state="VERIFIED",
            current_version=1,
            is_active=True,
        )
    )
    db_session.commit()

    r = client.get("/api/v1/scholarships?study_scope=international_abroad&destination_country=United%20Kingdom&funding_type=full_funding")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["destination_countries"] == ["United Kingdom"]

    # Register & chat with mocked live web verifier
    client.post(
        "/api/v1/auth/register",
        json={"email": "intl@example.com", "password": "Password1234!"},
    )
    client.put(
        "/api/v1/profile",
        json={
            "nationality": "India",
            "study_scope_preference": "abroad",
            "preferred_destination_countries": ["United Kingdom"],
            "education_level": "postgraduate",
        },
    )

    from app.agent import tools as agent_tools_mod

    orig_discover = agent_tools_mod.discover_and_verify_official_sites
    agent_tools_mod.discover_and_verify_official_sites = lambda *a, **kw: {
        "live_web_enabled": True,
        "sites_queried": 1,
        "verified_results": [
            {
                "title": "Commonwealth Master's Scholarships (UK FCDO)",
                "url": "https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
                "http_status": 200,
                "verified_live": True,
                "checked_at": now,
                "excerpt": "Full scholarships for Commonwealth citizens including India for Master's study in the UK.",
                "discovered_links": [],
                "error": None,
            }
        ],
        "unreachable_results": [],
    }
    try:
        chat = client.post(
            "/api/v1/assistant/chat",
            json={"message": "Find fully funded Master's scholarships in UK for Indian students"},
        )
        assert chat.status_code == 200
        body = chat.json()
        assert "discover_and_verify_official_web" in body["tool_calls_used"]
        assert len(body["live_verifications"]) == 1
        assert body["live_verifications"][0]["verified_live"] is True
        assert body["live_verifications"][0]["http_status"] == 200
    finally:
        agent_tools_mod.discover_and_verify_official_sites = orig_discover
