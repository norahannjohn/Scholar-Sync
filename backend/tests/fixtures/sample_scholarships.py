"""TEST FIXTURES ONLY — clearly labelled test records, never loaded in production."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.rag import GuidelineChunk, GuidelineDocument
from app.models.scholarship import Scholarship, ScholarshipSource


def seed_test_scholarships(db: Session) -> dict[str, Scholarship]:
    now = datetime.now(UTC)
    src = ScholarshipSource(
        name="TEST FIXTURE Official Source",
        owner_provider="Test Ministry",
        url="https://example.gov.in/test-scholarships",
        source_type="official_html",
        collection_method="http_html",
        adapter_key=None,
        check_interval_hours=24,
        is_active=True,
        last_checked_at=now,
        last_successful_at=now,
    )
    db.add(src)
    db.flush()

    s1 = Scholarship(
        slug="test-fixture-stem-women",
        name="TEST FIXTURE — STEM Women Scholarship",
        provider="Test Statutory Body",
        provider_type="statutory_body",
        scholarship_type="women_in_stem",
        description="Test fixture scholarship for female engineering students.",
        applicable_states=["All India"],
        education_levels=["undergraduate"],
        courses=["Engineering & Technology"],
        benefit_amount_display="₹50,000 per annum",
        benefit_amount_inr=50000,
        benefit_type="Annual grant",
        structured_rules={
            "version": 1,
            "criteria": [
                {
                    "key": "gender_f",
                    "label": "Female student",
                    "field": "gender",
                    "operator": "eq",
                    "value": "female",
                    "description": "Must be a female student.",
                    "mandatory": True,
                    "source_reference": "Test Guideline Sec 2.1",
                },
                {
                    "key": "ug_level",
                    "label": "Undergraduate",
                    "field": "education_level",
                    "operator": "eq",
                    "value": "undergraduate",
                    "description": "Pursuing undergraduate degree.",
                    "mandatory": True,
                },
                {
                    "key": "income_cap",
                    "label": "Family income ≤ ₹8,00,000",
                    "field": "annual_family_income_inr",
                    "operator": "max",
                    "value": 800000,
                    "description": "Annual family income must not exceed ₹8,00,000.",
                    "mandatory": True,
                },
            ],
        },
        required_documents=[
            {
                "item": "State Income Certificate",
                "status": "required",
                "note": "Annual family income <= Rs. 8 lakh.",
            },
            {
                "item": "Admission Confirmation Letter",
                "status": "confirm_with_provider",
                "note": "Confirm institute attestation format.",
            },
        ],
        application_steps=[
            "Create account on the official portal.",
            "Upload required details and submit before deadline.",
        ],
        application_start_date=date(2026, 10, 1),
        application_deadline=date(2026, 12, 31),
        status="OPEN",
        status_reason="Test open window",
        official_info_url="https://example.gov.in/stem-women",
        official_application_url="https://example.gov.in/apply",
        source_id=src.id,
        source_type="official_html",
        source_url="https://example.gov.in/stem-women",
        last_checked_at=now,
        last_verified_at=now,
        verification_state="VERIFIED",
        current_version=1,
        is_active=True,
    )

    s2 = Scholarship(
        slug="test-fixture-ner-merit",
        name="TEST FIXTURE — North East Merit Grant",
        provider="Test Regional Board",
        provider_type="central_government",
        scholarship_type="merit",
        description="Test fixture scholarship for North Eastern states.",
        applicable_states=["Assam", "Meghalaya", "Tripura"],
        education_levels=["undergraduate", "postgraduate"],
        courses=["All Disciplines"],
        benefit_amount_display="₹30,000 per annum",
        benefit_amount_inr=30000,
        benefit_type="Annual grant",
        structured_rules={
            "version": 1,
            "criteria": [
                {
                    "key": "ner_state",
                    "label": "Domicile state",
                    "field": "state_ut",
                    "operator": "in",
                    "value": ["Assam", "Meghalaya", "Tripura"],
                    "description": "Domicile of Assam, Meghalaya, or Tripura.",
                    "mandatory": True,
                },
                {
                    "key": "min_marks",
                    "label": "Minimum 75% marks",
                    "field": "academic_score",
                    "operator": "academic_min_percentage",
                    "value": 75,
                    "min_cgpa_10": 8.0,
                    "description": "Minimum 75% (or 8.0 CGPA/10).",
                    "mandatory": True,
                },
            ],
        },
        required_documents=[],
        application_steps=[],
        application_start_date=date(2026, 10, 15),
        application_deadline=date(2027, 2, 15),
        status="OPEN",
        status_reason="Open",
        official_info_url="https://example.gov.in/ner",
        official_application_url="https://example.gov.in/ner-apply",
        source_id=src.id,
        source_type="official_pdf",
        source_url="https://example.gov.in/ner.pdf",
        last_checked_at=now,
        last_verified_at=now,
        verification_state="VERIFIED",
        current_version=1,
        is_active=True,
    )

    db.add_all([s1, s2])
    db.flush()

    doc = GuidelineDocument(
        scholarship_id=s1.id,
        title="TEST FIXTURE Official STEM Women Guidelines",
        provider="Test Statutory Body",
        source_url="https://example.gov.in/stem-women.pdf",
        document_type="pdf",
        content_hash="abc123",
        extraction_status="INDEXED",
        verification_status="VERIFIED",
        retrieved_at=now,
    )
    db.add(doc)
    db.flush()

    db.add(
        GuidelineChunk(
            document_id=doc.id,
            scholarship_id=s1.id,
            chunk_index=0,
            section_heading="Eligibility & Income Cap",
            page_number=2,
            content=(
                "Section 2.1: Female students admitted to first year undergraduate technical "
                "degree courses with annual family income not exceeding Rs. 8,00,000 are eligible. "
                "A valid income certificate issued by the competent State/UT authority is required."
            ),
            source_url="https://example.gov.in/stem-women.pdf",
            verification_status="VERIFIED",
            retrieved_at=now,
        )
    )
    db.commit()
    return {"stem": s1, "ner": s2}
