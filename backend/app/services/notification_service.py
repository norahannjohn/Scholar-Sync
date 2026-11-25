from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.eligibility.engine import evaluate_eligibility
from app.models.scholarship import Scholarship
from app.models.tracking import Notification, SavedScholarship
from app.models.user import StudentProfile


def profile_to_dict(profile: StudentProfile | None) -> dict:
    if not profile:
        return {}
    return {
        "display_name": profile.display_name,
        "nationality": profile.nationality,
        "state_ut": profile.state_ut,
        "study_scope_preference": profile.study_scope_preference,
        "preferred_destination_countries": profile.preferred_destination_countries or [],
        "target_university": profile.target_university,
        "preferred_funding_types": profile.preferred_funding_types or [],
        "english_proficiency_test": profile.english_proficiency_test,
        "work_experience_years": profile.work_experience_years,
        "education_level": profile.education_level,
        "course_field": profile.course_field,
        "current_year_or_grade": profile.current_year_or_grade,
        "institution_name": profile.institution_name,
        "institution_type": profile.institution_type,
        "grading_scale": profile.grading_scale,
        "academic_score": profile.academic_score,
        "class12_board_percentile": profile.class12_board_percentile,
        "annual_family_income_inr": profile.annual_family_income_inr,
        "category": profile.category,
        "gender": profile.gender,
        "disability_percentage": profile.disability_percentage,
        "is_single_girl_child": profile.is_single_girl_child,
        "is_orphan_or_martyr_ward": profile.is_orphan_or_martyr_ward,
        "age_years": profile.age_years,
        "study_mode": profile.study_mode,
        "receiving_other_scholarship": profile.receiving_other_scholarship,
    }


def notify_affected_users_of_scholarship_change(
    db: Session,
    *,
    scholarship: Scholarship,
    changed_fields: dict,
) -> int:
    """Create in-app notifications for users who saved or potentially match a changed scholarship."""
    if not changed_fields:
        return 0
    important_keys = {"application_deadline", "status", "structured_rules", "benefit_amount_display"}
    relevant_changes = [k for k in changed_fields.keys() if k in important_keys]
    if not relevant_changes:
        return 0

    saved_user_ids = set(
        db.scalars(
            select(SavedScholarship.user_id).where(
                SavedScholarship.scholarship_id == scholarship.id
            )
        ).all()
    )

    profiles = list(
        db.scalars(select(StudentProfile).where(StudentProfile.consent_matching.is_(True))).all()
    )
    matched_user_ids: set[str] = set()
    for prof in profiles:
        if prof.user_id in saved_user_ids:
            continue
        ev = evaluate_eligibility(scholarship.structured_rules, profile_to_dict(prof))
        if ev.overall_status == "POTENTIAL_MATCH":
            matched_user_ids.add(prof.user_id)

    target_user_ids = saved_user_ids | matched_user_ids
    if not target_user_ids:
        return 0

    change_summary = ", ".join(k.replace("_", " ") for k in relevant_changes)
    created = 0
    for uid in target_user_ids:
        db.add(
            Notification(
                user_id=uid,
                scholarship_id=scholarship.id,
                title=f"Official update: {scholarship.name}",
                message=(
                    f"Detected update from official source ({change_summary}). "
                    f"Current status: {scholarship.status}. Please review the official portal details."
                ),
                notification_type="scholarship_update",
            )
        )
        created += 1
    db.flush()
    return created
