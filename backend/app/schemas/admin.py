from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    owner_provider: str = Field(..., min_length=2, max_length=200)
    url: str = Field(..., min_length=8, max_length=1000)
    source_type: Literal["official_html", "official_pdf", "official_api", "manual_admin"]
    collection_method: Literal["http_html", "http_pdf", "http_json", "manual"]
    adapter_key: str | None = Field(default=None, max_length=100)
    check_interval_hours: int = Field(default=24, ge=1, le=720)
    is_active: bool = True
    access_notes: str | None = None


class SourceResponse(BaseModel):
    id: str
    name: str
    owner_provider: str
    url: str
    source_type: str
    collection_method: str
    adapter_key: str | None
    check_interval_hours: int
    is_active: bool
    last_checked_at: datetime | None
    last_successful_at: datetime | None
    last_content_hash: str | None
    last_error: str | None
    access_notes: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceCheckLogResponse(BaseModel):
    id: str
    source_id: str
    checked_at: datetime
    http_status: int | None
    success: bool
    content_hash: str | None
    change_detected: bool
    auto_updated_count: int
    summary: str | None
    error_message: str | None

    model_config = {"from_attributes": True}


class SyncRunResponse(BaseModel):
    sources_checked: int
    sources_succeeded: int
    sources_failed: int
    changes_detected: int
    scholarships_updated: int
    documents_reindexed: int
    details: list[dict]
