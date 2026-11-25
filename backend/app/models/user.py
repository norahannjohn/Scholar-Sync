from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    profile: Mapped[StudentProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_ut: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    study_scope_preference: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preferred_destination_countries: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    target_university: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred_funding_types: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    english_proficiency_test: Mapped[str | None] = mapped_column(String(80), nullable=True)
    work_experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    course_field: Mapped[str | None] = mapped_column(String(150), nullable=True)
    current_year_or_grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    institution_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    institution_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    grading_scale: Mapped[str | None] = mapped_column(String(30), nullable=True)
    academic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    class12_board_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_family_income_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    disability_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_single_girl_child: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_orphan_or_martyr_ward: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    study_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    receiving_other_scholarship: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_matching: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profile")

    __table_args__ = (
        Index("ix_student_profiles_state_level", "state_ut", "education_level"),
    )
