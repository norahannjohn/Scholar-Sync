from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import CollectorOutcome, ExtractedScholarshipUpdate
from app.models.scholarship import ScholarshipSource, ScholarshipVersion
from app.models.tracking import Notification, SavedScholarship
from app.monitoring.sync_service import sync_single_source
from app.services.auth_service import register_user
from tests.fixtures.sample_scholarships import seed_test_scholarships


def test_source_failure_marks_stale_and_logs(db_session: Session) -> None:
    schols = seed_test_scholarships(db_session)
    stem = schols["stem"]
    stem.last_verified_at = datetime.now(UTC) - timedelta(days=20)
    db_session.add(stem)
    db_session.commit()

    src = db_session.scalar(select(ScholarshipSource).where(ScholarshipSource.id == stem.source_id))
    assert src is not None

    from app.monitoring import sync_service

    orig = sync_service._run_collector_for_source
    sync_service._run_collector_for_source = lambda _s: CollectorOutcome(
        success=False,
        http_status=503,
        content_hash=None,
        summary="Upstream unavailable",
        error_message="HTTP 503 Service Unavailable",
    )
    try:
        res = sync_single_source(db_session, src, stale_after_days=14)
        assert res["success"] is False
        db_session.refresh(stem)
        assert stem.verification_state == "STALE"
    finally:
        sync_service._run_collector_for_source = orig


def test_auto_update_creates_version_and_notifies_saved_users(db_session: Session) -> None:
    schols = seed_test_scholarships(db_session)
    stem = schols["stem"]
    user = register_user(db_session, email="notify@example.com", password="Password1234!")
    db_session.add(SavedScholarship(user_id=user.id, scholarship_id=stem.id))
    db_session.commit()

    src = db_session.scalar(select(ScholarshipSource).where(ScholarshipSource.id == stem.source_id))
    assert src is not None

    from datetime import date

    from app.monitoring import sync_service

    orig = sync_service._run_collector_for_source
    sync_service._run_collector_for_source = lambda _s: CollectorOutcome(
        success=True,
        http_status=200,
        content_hash="newhash999",
        summary="Updated deadline detected",
        scholarship_updates=[
            ExtractedScholarshipUpdate(
                slug=stem.slug,
                application_deadline=date(2027, 1, 15),
                status="OPEN",
                status_reason="Extended to 2027-01-15",
                confidence="high",
            )
        ],
    )
    try:
        res = sync_single_source(db_session, src)
        assert res["success"] is True
        assert res["change_detected"] is True
        assert res["scholarships_updated"] == 1

        db_session.refresh(stem)
        assert stem.application_deadline == date(2027, 1, 15)
        assert stem.current_version == 2

        versions = list(
            db_session.scalars(
                select(ScholarshipVersion).where(ScholarshipVersion.scholarship_id == stem.id)
            ).all()
        )
        assert len(versions) == 1
        assert "application_deadline" in versions[0].changed_fields

        notifs = list(
            db_session.scalars(select(Notification).where(Notification.user_id == user.id)).all()
        )
        assert len(notifs) == 1
        assert "Official update" in notifs[0].title
    finally:
        sync_service._run_collector_for_source = orig


def test_rag_and_assistant_no_key_fallback_and_e2e_journey(
    client: TestClient, db_session: Session
) -> None:
    schols = seed_test_scholarships(db_session)
    stem_id = schols["stem"].id

    # 1. Register
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "e2e@example.com", "password": "E2EPassword123!", "full_name": "Meera"},
    )
    assert reg.status_code == 201

    # 2. Complete profile
    prof = client.put(
        "/api/v1/profile",
        json={
            "state_ut": "Tamil Nadu",
            "education_level": "undergraduate",
            "course_field": "B.E. Computer Science",
            "gender": "female",
            "annual_family_income_inr": 420000,
            "academic_score": 88.5,
            "grading_scale": "percentage",
            "study_mode": "regular",
        },
    )
    assert prof.status_code == 200

    # 3. Discover scholarships
    disc = client.get("/api/v1/scholarships")
    assert disc.status_code == 200
    items = disc.json()["items"]
    assert items[0]["id"] == stem_id
    assert items[0]["eligibility"]["overall_status"] == "POTENTIAL_MATCH"

    # 4. Open detail & view eligibility explanation
    detail = client.get(f"/api/v1/scholarships/{stem_id}")
    assert detail.status_code == 200
    assert len(detail.json()["evidence_snippets"]) == 1
    assert detail.json()["eligibility"]["overall_status"] == "POTENTIAL_MATCH"

    # 5. Assistant no-key fallback & checklist
    chk = client.get(f"/api/v1/assistant/checklist/{stem_id}")
    assert chk.status_code == 200
    assert len(chk.json()["items"]) == 2

    chat = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Am I eligible and what income proof is needed?", "scholarship_id": stem_id},
    )
    assert chat.status_code == 200
    chat_body = chat.json()
    assert chat_body["mode"] == "fallback_no_key"
    assert chat_body["gemini_configured"] is False
    assert len(chat_body["citations"]) >= 1
    assert chat_body["citations"][0]["page_number"] == 2

    # 6. Save scholarship
    saved = client.post("/api/v1/saved", json={"scholarship_id": stem_id})
    assert saved.status_code == 201

    # 7. Update tracking status
    app_create = client.post(
        "/api/v1/applications",
        json={"scholarship_id": stem_id, "status": "PREPARING", "notes": "Collecting income certificate"},
    )
    assert app_create.status_code == 201
    app_id = app_create.json()["id"]

    app_patch = client.patch(
        f"/api/v1/applications/{app_id}",
        json={"status": "READY_TO_APPLY"},
    )
    assert app_patch.status_code == 200
    assert app_patch.json()["status"] == "READY_TO_APPLY"
    assert app_patch.json()["is_user_maintained"] is True
