from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import utcnow


class ScholarshipSource(Base):
    __tablename__ = "scholarship_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_provider: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    collection_method: Mapped[str] = mapped_column(String(60), nullable=False)
    adapter_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    check_interval_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    scholarships: Mapped[list[Scholarship]] = relationship(back_populates="source")
    check_logs: Mapped[list[SourceCheckLog]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Scholarship(Base):
    __tablename__ = "scholarships"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    scholarship_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    study_scope: Mapped[str] = mapped_column(
        String(30), default="india", index=True, nullable=False
    )  # india | international_abroad | global
    destination_countries: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    target_universities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    eligible_nationalities: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: ["India"], nullable=False
    )
    funding_type: Mapped[str] = mapped_column(
        String(50), default="partial_grant", index=True, nullable=False
    )  # full_funding | tuition_only | stipend_allowance | partial_grant | fellowship

    applicable_states: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    education_levels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    courses: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    institution_constraints: Mapped[str | None] = mapped_column(Text, nullable=True)

    benefit_amount_display: Mapped[str | None] = mapped_column(String(200), nullable=True)
    benefit_amount_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    benefit_type: Mapped[str | None] = mapped_column(String(80), nullable=True)

    structured_rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_documents: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    application_steps: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    application_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    application_deadline: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    deadline_timezone: Mapped[str] = mapped_column(
        String(60), default="Asia/Kolkata (IST)", nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), default="UNKNOWN", index=True, nullable=False)
    status_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)

    official_info_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    official_application_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("scholarship_sources.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_state: Mapped[str] = mapped_column(
        String(30), default="UNVERIFIED", index=True, nullable=False
    )
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    source: Mapped[ScholarshipSource | None] = relationship(back_populates="scholarships")
    versions: Mapped[list[ScholarshipVersion]] = relationship(
        back_populates="scholarship",
        cascade="all, delete-orphan",
        order_by="ScholarshipVersion.version_number.desc()",
    )

    __table_args__ = (
        Index("ix_scholarships_status_deadline", "status", "application_deadline"),
    )


class ScholarshipVersion(Base):
    __tablename__ = "scholarship_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scholarship_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scholarships.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    changed_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    change_source: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    scholarship: Mapped[Scholarship] = relationship(back_populates="versions")


class SourceCheckLog(Base):
    __tablename__ = "source_check_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scholarship_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True, nullable=False
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_updated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[ScholarshipSource] = relationship(back_populates="check_logs")
