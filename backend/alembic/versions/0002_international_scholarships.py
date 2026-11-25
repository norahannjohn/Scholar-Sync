"""Add international scholarship & student study-abroad fields

Revision ID: 0002_international_scholarships
Revises: 0001_initial_schema
Create Date: 2026-11-25 16:05:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_international_scholarships"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_profiles", sa.Column("nationality", sa.String(length=100), nullable=True))
    op.add_column(
        "student_profiles",
        sa.Column("study_scope_preference", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "student_profiles",
        sa.Column(
            "preferred_destination_countries",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "student_profiles", sa.Column("target_university", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "student_profiles",
        sa.Column(
            "preferred_funding_types",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "student_profiles",
        sa.Column("english_proficiency_test", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "student_profiles", sa.Column("work_experience_years", sa.Float(), nullable=True)
    )

    op.add_column(
        "scholarships",
        sa.Column("study_scope", sa.String(length=30), nullable=False, server_default="india"),
    )
    op.add_column(
        "scholarships",
        sa.Column(
            "destination_countries",
            sa.JSON(),
            nullable=False,
            server_default='["India"]',
        ),
    )
    op.add_column(
        "scholarships",
        sa.Column(
            "target_universities",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "scholarships",
        sa.Column(
            "eligible_nationalities",
            sa.JSON(),
            nullable=False,
            server_default='["India"]',
        ),
    )
    op.add_column(
        "scholarships",
        sa.Column(
            "funding_type",
            sa.String(length=50),
            nullable=False,
            server_default="partial_grant",
        ),
    )
    op.create_index("ix_scholarships_study_scope", "scholarships", ["study_scope"])
    op.create_index("ix_scholarships_funding_type", "scholarships", ["funding_type"])


def downgrade() -> None:
    op.drop_index("ix_scholarships_funding_type", table_name="scholarships")
    op.drop_index("ix_scholarships_study_scope", table_name="scholarships")
    op.drop_column("scholarships", "funding_type")
    op.drop_column("scholarships", "eligible_nationalities")
    op.drop_column("scholarships", "target_universities")
    op.drop_column("scholarships", "destination_countries")
    op.drop_column("scholarships", "study_scope")

    op.drop_column("student_profiles", "work_experience_years")
    op.drop_column("student_profiles", "english_proficiency_test")
    op.drop_column("student_profiles", "preferred_funding_types")
    op.drop_column("student_profiles", "target_university")
    op.drop_column("student_profiles", "preferred_destination_countries")
    op.drop_column("student_profiles", "study_scope_preference")
    op.drop_column("student_profiles", "nationality")
