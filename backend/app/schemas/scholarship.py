from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.eligibility.rules_schema import RuleSet
from app.schemas.eligibility import EligibilityEvaluationSchema


class RequiredDocumentItem(BaseModel):
    item: str
    status: str  # required | conditional | confirm_with_provider
    note: str | None = None


class EvidenceSnippetSchema(BaseModel):
    chunk_id: str
    document_title: str
    source_url: str
    page_number: int | None = None
    section_heading: str | None = None
    verification_status: str
    retrieved_at: datetime
    excerpt: str


class ScholarshipVersionSchema(BaseModel):
    id: str
    version_number: int
    changed_fields: dict[str, Any]
    change_source: str
    source_url: str | None
    reviewed: bool
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScholarshipListItem(BaseModel):
    id: str
    slug: str
    name: str
    provider: str
    provider_type: str
    scholarship_type: str
    description: str
    study_scope: str
    destination_countries: list[str]
    target_universities: list[str]
    eligible_nationalities: list[str]
    funding_type: str
    applicable_states: list[str]
    education_levels: list[str]
    courses: list[str]
    benefit_amount_display: str | None
    benefit_amount_inr: int | None
    benefit_type: str | None
    application_start_date: date | None
    application_deadline: date | None
    deadline_timezone: str
    status: str
    status_reason: str | None
    official_info_url: str
    official_application_url: str | None
    source_type: str
    source_url: str
    last_checked_at: datetime | None
    last_verified_at: datetime | None
    verification_state: str
    current_version: int
    eligibility: EligibilityEvaluationSchema | None = None
    match_reason: str | None = None
    is_saved: bool = False


class ScholarshipDetail(ScholarshipListItem):
    institution_constraints: str | None = None
    structured_rules: dict[str, Any]
    required_documents: list[dict[str, Any]]
    application_steps: list[str]
    source_publication_date: date | None = None
    evidence_snippets: list[EvidenceSnippetSchema] = Field(default_factory=list)
    recent_versions: list[ScholarshipVersionSchema] = Field(default_factory=list)


class ScholarshipListResponse(BaseModel):
    items: list[ScholarshipListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    available_filters: dict[str, list[str]]


class ScholarshipCreateUpdate(BaseModel):
    slug: str = Field(..., min_length=3, max_length=180)
    name: str = Field(..., min_length=3, max_length=250)
    provider: str = Field(..., min_length=2, max_length=200)
    provider_type: str = Field(..., max_length=60)
    scholarship_type: str = Field(..., max_length=60)
    description: str = Field(..., min_length=10)
    study_scope: str = Field(default="india", max_length=30)
    destination_countries: list[str] = Field(default_factory=lambda: ["India"])
    target_universities: list[str] = Field(default_factory=list)
    eligible_nationalities: list[str] = Field(default_factory=lambda: ["India"])
    funding_type: str = Field(default="partial_grant", max_length=50)
    applicable_states: list[str] = Field(default_factory=lambda: ["All India"])
    education_levels: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)
    institution_constraints: str | None = None
    benefit_amount_display: str | None = None
    benefit_amount_inr: int | None = None
    benefit_type: str | None = None
    structured_rules: RuleSet
    required_documents: list[RequiredDocumentItem] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)
    application_start_date: date | None = None
    application_deadline: date | None = None
    deadline_timezone: str = "Asia/Kolkata (IST)"
    status: str = "UNKNOWN"
    status_reason: str | None = None
    official_info_url: str = Field(..., max_length=1000)
    official_application_url: str | None = Field(default=None, max_length=1000)
    source_id: str | None = None
    source_type: str = "official_html"
    source_url: str = Field(..., max_length=1000)
    source_publication_date: date | None = None
    verification_state: str = "VERIFIED"
    is_active: bool = True
