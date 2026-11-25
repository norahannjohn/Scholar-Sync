from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.scholarship import Scholarship
from app.models.tracking import StudentApplication
from app.models.user import User, utcnow
from app.schemas.tracking import (
    ApplicationPatchRequest,
    ApplicationUpsertRequest,
    StudentApplicationResponse,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def _to_response(app_row: StudentApplication, schol: Scholarship) -> StudentApplicationResponse:
    return StudentApplicationResponse(
        id=app_row.id,
        scholarship_id=schol.id,
        scholarship_name=schol.name,
        provider=schol.provider,
        application_deadline=schol.application_deadline,
        scholarship_status=schol.status,
        official_application_url=schol.official_application_url,
        official_info_url=schol.official_info_url,
        status=app_row.status,
        notes=app_row.notes,
        updated_by_user_at=app_row.updated_by_user_at,
        created_at=app_row.created_at,
        is_user_maintained=True,
    )


@router.get("", response_model=list[StudentApplicationResponse])
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StudentApplicationResponse]:
    rows = list(
        db.execute(
            select(StudentApplication, Scholarship)
            .join(Scholarship, StudentApplication.scholarship_id == Scholarship.id)
            .where(StudentApplication.user_id == current_user.id)
            .order_by(StudentApplication.updated_by_user_at.desc())
        ).all()
    )
    return [_to_response(app_row, schol) for app_row, schol in rows]


@router.post("", response_model=StudentApplicationResponse, status_code=status.HTTP_201_CREATED)
def upsert_application(
    payload: ApplicationUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentApplicationResponse:
    schol = db.scalar(select(Scholarship).where(Scholarship.id == payload.scholarship_id))
    if not schol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found.")
    existing = db.scalar(
        select(StudentApplication).where(
            StudentApplication.user_id == current_user.id,
            StudentApplication.scholarship_id == schol.id,
        )
    )
    if existing:
        existing.status = payload.status
        existing.notes = payload.notes
        existing.updated_by_user_at = utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return _to_response(existing, schol)

    row = StudentApplication(
        user_id=current_user.id,
        scholarship_id=schol.id,
        status=payload.status,
        notes=payload.notes,
        updated_by_user_at=utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row, schol)


@router.patch("/{application_id}", response_model=StudentApplicationResponse)
def patch_application(
    application_id: str,
    payload: ApplicationPatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentApplicationResponse:
    row = db.scalar(
        select(StudentApplication).where(
            StudentApplication.id == application_id,
            StudentApplication.user_id == current_user.id,
        )
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application tracking record not found."
        )
    if payload.status is not None:
        row.status = payload.status
    if payload.notes is not None:
        row.notes = payload.notes
    row.updated_by_user_at = utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    schol = db.scalar(select(Scholarship).where(Scholarship.id == row.scholarship_id))
    assert schol is not None
    return _to_response(row, schol)


@router.delete("/{application_id}")
def delete_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(
        select(StudentApplication).where(
            StudentApplication.id == application_id,
            StudentApplication.user_id == current_user.id,
        )
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application tracking record not found."
        )
    db.delete(row)
    db.commit()
    return {"message": "Tracking record deleted."}
