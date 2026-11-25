from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.scholarship import (
    Scholarship,
    ScholarshipSource,
    ScholarshipVersion,
    SourceCheckLog,
)
from app.models.user import User
from app.monitoring.sync_service import sync_all_active_sources, sync_single_source
from app.schemas.admin import (
    SourceCheckLogResponse,
    SourceCreateRequest,
    SourceResponse,
    SyncRunResponse,
)
from app.schemas.scholarship import (
    ScholarshipCreateUpdate,
    ScholarshipDetail,
    ScholarshipVersionSchema,
)
from app.services.scholarship_service import (
    create_or_update_scholarship_admin,
    get_scholarship_detail,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/sources", response_model=list[SourceResponse])
def list_sources(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[SourceResponse]:
    rows = list(db.scalars(select(ScholarshipSource).order_by(ScholarshipSource.name.asc())).all())
    return [SourceResponse.model_validate(r) for r in rows]


@router.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreateRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> SourceResponse:
    existing = db.scalar(select(ScholarshipSource).where(ScholarshipSource.url == payload.url))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A source with this URL already exists."
        )
    src = ScholarshipSource(**payload.model_dump())
    db.add(src)
    db.commit()
    db.refresh(src)
    return SourceResponse.model_validate(src)


@router.get("/source-logs", response_model=list[SourceCheckLogResponse])
def list_source_logs(
    limit: int = 40,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[SourceCheckLogResponse]:
    rows = list(
        db.scalars(
            select(SourceCheckLog)
            .order_by(SourceCheckLog.checked_at.desc())
            .limit(min(max(limit, 1), 200))
        ).all()
    )
    return [SourceCheckLogResponse.model_validate(r) for r in rows]


@router.post("/sync", response_model=SyncRunResponse)
def run_sync_all(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> SyncRunResponse:
    settings = get_settings()
    summary = sync_all_active_sources(db, stale_after_days=settings.stale_after_days)
    return SyncRunResponse(**summary)


@router.post("/sources/{source_id}/sync")
def run_sync_one(
    source_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    src = db.scalar(select(ScholarshipSource).where(ScholarshipSource.id == source_id))
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    settings = get_settings()
    return sync_single_source(db, src, stale_after_days=settings.stale_after_days)


@router.post("/scholarships", response_model=ScholarshipDetail, status_code=status.HTTP_201_CREATED)
def admin_create_scholarship(
    payload: ScholarshipCreateUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> ScholarshipDetail:
    existing = db.scalar(select(Scholarship).where(Scholarship.slug == payload.slug))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scholarship with slug '{payload.slug}' already exists.",
        )
    s = create_or_update_scholarship_admin(db, payload=payload, admin_email=admin.email)
    detail = get_scholarship_detail(db, s.id, profile=None, saved_ids=set())
    assert detail is not None
    return detail


@router.put("/scholarships/{scholarship_id}", response_model=ScholarshipDetail)
def admin_update_scholarship(
    scholarship_id: str,
    payload: ScholarshipCreateUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> ScholarshipDetail:
    s = db.scalar(select(Scholarship).where(Scholarship.id == scholarship_id))
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scholarship not found.")
    updated = create_or_update_scholarship_admin(
        db, payload=payload, admin_email=admin.email, scholarship=s
    )
    detail = get_scholarship_detail(db, updated.id, profile=None, saved_ids=set())
    assert detail is not None
    return detail


@router.get("/versions", response_model=list[ScholarshipVersionSchema])
def list_versions(
    unreviewed_only: bool = False,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[ScholarshipVersionSchema]:
    stmt = select(ScholarshipVersion).order_by(ScholarshipVersion.created_at.desc()).limit(60)
    if unreviewed_only:
        stmt = stmt.where(ScholarshipVersion.reviewed.is_(False))
    rows = list(db.scalars(stmt).all())
    return [ScholarshipVersionSchema.model_validate(r) for r in rows]


@router.post("/versions/{version_id}/review", response_model=ScholarshipVersionSchema)
def mark_version_reviewed(
    version_id: str,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> ScholarshipVersionSchema:
    v = db.scalar(select(ScholarshipVersion).where(ScholarshipVersion.id == version_id))
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")
    now = datetime.now(UTC)
    v.reviewed = True
    v.reviewed_by = admin.email
    v.reviewed_at = now
    db.add(v)

    schol = db.scalar(select(Scholarship).where(Scholarship.id == v.scholarship_id))
    if schol:
        schol.verification_state = "VERIFIED"
        schol.last_verified_at = now
        db.add(schol)

    db.commit()
    db.refresh(v)
    return ScholarshipVersionSchema.model_validate(v)
