from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user
from app.db.session import get_db
from app.eligibility.engine import evaluate_eligibility
from app.models.scholarship import Scholarship
from app.models.user import StudentProfile, User
from app.schemas.eligibility import EligibilityEvaluationSchema
from app.schemas.scholarship import ScholarshipDetail, ScholarshipListResponse
from app.services.notification_service import profile_to_dict
from app.services.scholarship_service import (
    _to_eligibility_schema,
    get_scholarship_detail,
    get_user_saved_ids,
    list_scholarships_for_user,
)

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


@router.get("", response_model=ScholarshipListResponse)
def discover_scholarships(
    q: str | None = Query(default=None, max_length=200),
    study_scope: str | None = Query(default=None, max_length=30),
    destination_country: str | None = Query(default=None, max_length=100),
    funding_type: str | None = Query(default=None, max_length=50),
    university: str | None = Query(default=None, max_length=200),
    education_level: str | None = Query(default=None, max_length=50),
    state_ut: str | None = Query(default=None, max_length=100),
    scholarship_type: str | None = Query(default=None, max_length=60),
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    provider: str | None = Query(default=None, max_length=200),
    sort: str = Query(default="relevance", pattern="^(relevance|deadline|recently_verified)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ScholarshipListResponse:
    profile: StudentProfile | None = None
    saved_ids: set[str] = set()
    if current_user:
        profile = db.scalar(
            select(StudentProfile).where(StudentProfile.user_id == current_user.id)
        )
        saved_ids = get_user_saved_ids(db, current_user.id)

    return list_scholarships_for_user(
        db,
        profile=profile,
        saved_ids=saved_ids,
        q=q,
        study_scope=study_scope,
        destination_country=destination_country,
        funding_type=funding_type,
        university=university,
        education_level=education_level,
        state_ut=state_ut,
        scholarship_type=scholarship_type,
        status=status_filter,
        provider=provider,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/{scholarship_id}", response_model=ScholarshipDetail)
def get_scholarship(
    scholarship_id: str,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ScholarshipDetail:
    profile: StudentProfile | None = None
    saved_ids: set[str] = set()
    if current_user:
        profile = db.scalar(
            select(StudentProfile).where(StudentProfile.user_id == current_user.id)
        )
        saved_ids = get_user_saved_ids(db, current_user.id)

    detail = get_scholarship_detail(
        db, scholarship_id, profile=profile, saved_ids=saved_ids
    )
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scholarship not found.",
        )
    return detail


@router.get("/{scholarship_id}/eligibility", response_model=EligibilityEvaluationSchema)
@router.post("/{scholarship_id}/eligibility", response_model=EligibilityEvaluationSchema)
def evaluate_scholarship_eligibility(
    scholarship_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EligibilityEvaluationSchema:
    schol = db.scalar(
        select(Scholarship).where(
            or_(Scholarship.id == scholarship_id, Scholarship.slug == scholarship_id)
        )
    )
    if not schol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scholarship not found.",
        )
    profile = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    ev = evaluate_eligibility(schol.structured_rules, profile_to_dict(profile))
    return _to_eligibility_schema(ev)
