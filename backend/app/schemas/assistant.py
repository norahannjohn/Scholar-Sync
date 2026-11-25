from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CitationSchema(BaseModel):
    title: str
    source_url: str
    page_number: int | None = None
    section_heading: str | None = None
    verification_status: str
    excerpt: str


class LiveVerificationResult(BaseModel):
    title: str
    url: str
    http_status: int | None = None
    verified_live: bool
    checked_at: datetime
    excerpt: str | None = None
    discovered_links: list[dict[str, str]] = Field(default_factory=list)
    error: str | None = None


class ChecklistItemSchema(BaseModel):
    item: str
    requirement_level: str  # required | conditional | confirm_with_provider
    note: str | None = None
    source_url: str | None = None


class ChecklistResponse(BaseModel):
    scholarship_id: str
    scholarship_name: str
    official_info_url: str
    official_application_url: str | None
    verification_state: str
    items: list[ChecklistItemSchema]
    application_steps: list[str]
    disclaimer: str


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    scholarship_id: str | None = None


class AssistantChatResponse(BaseModel):
    reply: str
    mode: str  # gemini | fallback_no_key | fallback_error
    citations: list[CitationSchema] = Field(default_factory=list)
    live_verifications: list[LiveVerificationResult] = Field(default_factory=list)
    tool_calls_used: list[str] = Field(default_factory=list)
    gemini_configured: bool
    disclaimer: str


class AssistantHistoryItem(BaseModel):
    id: str
    scholarship_id: str | None
    role: str
    content: str
    citations: list[CitationSchema] = Field(default_factory=list)
    mode: str
    created_at: datetime
