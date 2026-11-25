"""Initial ScholarSync schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-25 15:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=True),
        sa.Column("state_ut", sa.String(length=100), nullable=True),
        sa.Column("education_level", sa.String(length=50), nullable=True),
        sa.Column("course_field", sa.String(length=150), nullable=True),
        sa.Column("current_year_or_grade", sa.Integer(), nullable=True),
        sa.Column("institution_name", sa.String(length=200), nullable=True),
        sa.Column("institution_type", sa.String(length=80), nullable=True),
        sa.Column("grading_scale", sa.String(length=30), nullable=True),
        sa.Column("academic_score", sa.Float(), nullable=True),
        sa.Column("class12_board_percentile", sa.Float(), nullable=True),
        sa.Column("annual_family_income_inr", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("gender", sa.String(length=30), nullable=True),
        sa.Column("disability_percentage", sa.Integer(), nullable=True),
        sa.Column("is_single_girl_child", sa.Boolean(), nullable=True),
        sa.Column("is_orphan_or_martyr_ward", sa.Boolean(), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("study_mode", sa.String(length=30), nullable=True),
        sa.Column("receiving_other_scholarship", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("consent_matching", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_student_profiles_state_ut", "student_profiles", ["state_ut"])
    op.create_index(
        "ix_student_profiles_education_level", "student_profiles", ["education_level"]
    )
    op.create_index(
        "ix_student_profiles_state_level",
        "student_profiles",
        ["state_ut", "education_level"],
    )

    op.create_table(
        "scholarship_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("owner_provider", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("collection_method", sa.String(length=60), nullable=False),
        sa.Column("adapter_key", sa.String(length=100), nullable=True),
        sa.Column("check_interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_content_hash", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("access_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )

    op.create_table(
        "scholarships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("provider", sa.String(length=200), nullable=False),
        sa.Column("provider_type", sa.String(length=60), nullable=False),
        sa.Column("scholarship_type", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("applicable_states", sa.JSON(), nullable=False),
        sa.Column("education_levels", sa.JSON(), nullable=False),
        sa.Column("courses", sa.JSON(), nullable=False),
        sa.Column("institution_constraints", sa.Text(), nullable=True),
        sa.Column("benefit_amount_display", sa.String(length=200), nullable=True),
        sa.Column("benefit_amount_inr", sa.Integer(), nullable=True),
        sa.Column("benefit_type", sa.String(length=80), nullable=True),
        sa.Column("structured_rules", sa.JSON(), nullable=False),
        sa.Column("required_documents", sa.JSON(), nullable=False),
        sa.Column("application_steps", sa.JSON(), nullable=False),
        sa.Column("application_start_date", sa.Date(), nullable=True),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column("deadline_timezone", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("status_reason", sa.String(length=300), nullable=True),
        sa.Column("official_info_url", sa.String(length=1000), nullable=False),
        sa.Column("official_application_url", sa.String(length=1000), nullable=True),
        sa.Column("source_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_publication_date", sa.Date(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_state", sa.String(length=30), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["scholarship_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_scholarships_name", "scholarships", ["name"])
    op.create_index("ix_scholarships_provider", "scholarships", ["provider"])
    op.create_index("ix_scholarships_provider_type", "scholarships", ["provider_type"])
    op.create_index("ix_scholarships_scholarship_type", "scholarships", ["scholarship_type"])
    op.create_index("ix_scholarships_application_deadline", "scholarships", ["application_deadline"])
    op.create_index("ix_scholarships_status", "scholarships", ["status"])
    op.create_index("ix_scholarships_verification_state", "scholarships", ["verification_state"])
    op.create_index(
        "ix_scholarships_status_deadline", "scholarships", ["status", "application_deadline"]
    )

    op.create_table(
        "scholarship_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scholarship_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("change_source", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_by", sa.String(length=200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scholarship_versions_scholarship_id", "scholarship_versions", ["scholarship_id"]
    )

    op.create_table(
        "source_check_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("change_detected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["scholarship_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_check_logs_source_id", "source_check_logs", ["source_id"])
    op.create_index("ix_source_check_logs_checked_at", "source_check_logs", ["checked_at"])

    op.create_table(
        "saved_scholarships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("scholarship_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scholarship_id", name="uq_saved_user_scholarship"),
    )
    op.create_index("ix_saved_scholarships_user_id", "saved_scholarships", ["user_id"])
    op.create_index(
        "ix_saved_scholarships_scholarship_id", "saved_scholarships", ["scholarship_id"]
    )

    op.create_table(
        "student_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("scholarship_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_by_user_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scholarship_id", name="uq_app_user_scholarship"),
    )
    op.create_index("ix_student_applications_user_id", "student_applications", ["user_id"])
    op.create_index(
        "ix_student_applications_scholarship_id", "student_applications", ["scholarship_id"]
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("scholarship_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "guideline_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scholarship_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("provider", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("document_type", sa.String(length=30), nullable=False),
        sa.Column("document_version", sa.String(length=80), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("extraction_status", sa.String(length=30), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_guideline_documents_scholarship_id", "guideline_documents", ["scholarship_id"]
    )

    op.create_table(
        "guideline_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("scholarship_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_heading", sa.String(length=250), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("document_version", sa.String(length=80), nullable=True),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["guideline_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guideline_chunks_document_id", "guideline_chunks", ["document_id"])
    op.create_index("ix_guideline_chunks_scholarship_id", "guideline_chunks", ["scholarship_id"])
    op.create_index(
        "ix_guideline_chunks_scholarship_chunk",
        "guideline_chunks",
        ["scholarship_id", "chunk_index"],
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_guideline_chunks_fts ON guideline_chunks "
            "USING GIN (to_tsvector('english', content))"
        )

    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("scholarship_id", sa.String(length=36), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.Text(), nullable=True),
        sa.Column("mode", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scholarship_id"], ["scholarships.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_messages_user_id", "assistant_messages", ["user_id"])
    op.create_index("ix_assistant_messages_created_at", "assistant_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("assistant_messages")
    op.drop_table("guideline_chunks")
    op.drop_table("guideline_documents")
    op.drop_table("notifications")
    op.drop_table("student_applications")
    op.drop_table("saved_scholarships")
    op.drop_table("source_check_logs")
    op.drop_table("scholarship_versions")
    op.drop_table("scholarships")
    op.drop_table("scholarship_sources")
    op.drop_table("student_profiles")
    op.drop_table("user_sessions")
    op.drop_table("users")
