from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.eligibility.engine import evaluate_eligibility
from app.models.scholarship import Scholarship
from app.models.tracking import SavedScholarship
from app.models.user import StudentProfile, User
from app.schemas.tracking import SavedScholarshipResponse, SaveScholarshipRequest
from app.services.notification_service import profile_to_dict

router = APIRouter(prefix="/saved", tags=["saved"])


@router.get("", response_model=list[SavedScholarshipResponse])
def list_saved(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedScholarshipResponse]:
    profile = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    prof_dict = profile_to_dict(profile)
    rows = list(
        db.execute(
            select(SavedScholarship, Scholarship)
            .join(Scholarship, SavedScholarship.scholarship_id == Scholarship.id)
            .where(SavedScholarship.user_id == current_user.id)
            .order_by(SavedScholarship.created_at.desc())
        ).all()
    )
    out: list[SavedScholarshipResponse] = []
    for saved, schol in rows:
        ev = evaluate_eligibility(schol.structured_rules, prof_dict) if profile else None
        out.append(
            SavedScholarshipResponse(
                id=saved.id,
                scholarship_id=schol.id,
                scholarship_name=schol.name,
                provider=schol.provider,
                application_deadline=schol.application_deadline,
                status=schol.status,
                verification_state=schol.verification_state,
                last_checked_at=schol.last_checked_at,
                official_info_url=schol.official_info_url,
                eligibility_status=ev.overall_status if ev else None,
                eligibility_label=ev.overall_label if ev else None,
                created_at=saved.created_at,
            )
        )
    return out


@router.post("", response_model=SavedScholarshipResponse, status_code=status.HTTP_201_CREATED)
def save_scholarship(
    payload: SaveScholarshipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedScholarshipResponse:
    schol = db.scalar(select(Scholarship).where(Scholarship.id == payload.scholarship_id))
    if not schol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found.")
    existing = db.scalar(
        select(SavedScholarship).where(
            SavedScholarship.user_id == current_user.id,
            SavedScholarship.scholarship_id == schol.id,
        )
    )
    if not existing:
        existing = SavedScholarship(user_id=current_user.id, scholarship_id=schol.id)
        db.add(existing)
        db.commit()
        db.refresh(existing)

    profile = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    ev = evaluate_eligibility(schol.structured_rules, profile_to_dict(profile)) if profile else None
    return SavedScholarshipResponse(
        id=existing.id,
        scholarship_id=schol.id,
        scholarship_name=schol.name,
        provider=schol.provider,
        application_deadline=schol.application_deadline,
        status=schol.status,
        verification_state=schol.verification_state,
        last_checked_at=schol.last_checked_at,
        official_info_url=schol.official_info_url,
        eligibility_status=ev.overall_status if ev else None,
        eligibility_label=ev.overall_label if ev else None,
        created_at=existing.created_at,
    )


@router.delete("/{scholarship_id}")
def unsave_scholarship(
    scholarship_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    saved = db.scalar(
        select(SavedScholarship).where(
            SavedScholarship.user_id == current_user.id,
            SavedScholarship.scholarship_id == scholarship_id,
        )
    )
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Saved scholarship not found."
        )
    db.delete(saved)
    db.commit()
    return {"message": "Removed from saved scholarships."}
