from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import StudentProfile, User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/profile", tags=["profile"])

CORE_MATCH_FIELDS = [
    "nationality",
    "state_ut",
    "study_scope_preference",
    "education_level",
    "course_field",
    "academic_score",
    "study_mode",
]


def _serialize_profile(profile: StudentProfile) -> ProfileResponse:
    filled = sum(1 for f in CORE_MATCH_FIELDS if getattr(profile, f) is not None)
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        nationality=profile.nationality,
        state_ut=profile.state_ut,
        study_scope_preference=profile.study_scope_preference,
        preferred_destination_countries=profile.preferred_destination_countries or [],
        target_university=profile.target_university,
        preferred_funding_types=profile.preferred_funding_types or [],
        english_proficiency_test=profile.english_proficiency_test,
        work_experience_years=profile.work_experience_years,
        education_level=profile.education_level,
        course_field=profile.course_field,
        current_year_or_grade=profile.current_year_or_grade,
        institution_name=profile.institution_name,
        institution_type=profile.institution_type,
        grading_scale=profile.grading_scale,
        academic_score=profile.academic_score,
        class12_board_percentile=profile.class12_board_percentile,
        annual_family_income_inr=profile.annual_family_income_inr,
        category=profile.category,
        gender=profile.gender,
        disability_percentage=profile.disability_percentage,
        is_single_girl_child=profile.is_single_girl_child,
        is_orphan_or_martyr_ward=profile.is_orphan_or_martyr_ward,
        age_years=profile.age_years,
        study_mode=profile.study_mode,
        receiving_other_scholarship=profile.receiving_other_scholarship,
        notes=profile.notes,
        consent_matching=profile.consent_matching,
        completeness_fields_filled=filled,
        completeness_total_core=len(CORE_MATCH_FIELDS),
        updated_at=profile.updated_at,
    )


def _get_or_create_profile(db: Session, user: User) -> StudentProfile:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if not profile:
        profile = StudentProfile(user_id=user.id, display_name=user.full_name)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    profile = _get_or_create_profile(db, current_user)
    return _serialize_profile(profile)


@router.put("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    profile = _get_or_create_profile(db, current_user)
    for field, value in payload.model_dump().items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(profile, field, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)
