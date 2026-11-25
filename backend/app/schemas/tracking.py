from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ApplicationProgressStatus = Literal[
    "INTERESTED",
    "PREPARING",
    "READY_TO_APPLY",
    "SUBMITTED",
    "AWAITING_UPDATE",
    "AWARDED",
    "NOT_SELECTED",
]


class SaveScholarshipRequest(BaseModel):
    scholarship_id: str


class SavedScholarshipResponse(BaseModel):
    id: str
    scholarship_id: str
    scholarship_name: str
    provider: str
    application_deadline: date | None
    status: str
    verification_state: str
    last_checked_at: datetime | None
    official_info_url: str
    eligibility_status: str | None = None
    eligibility_label: str | None = None
    created_at: datetime


class ApplicationUpsertRequest(BaseModel):
    scholarship_id: str
    status: ApplicationProgressStatus = "INTERESTED"
    notes: str | None = Field(default=None, max_length=2000)


class ApplicationPatchRequest(BaseModel):
    status: ApplicationProgressStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class StudentApplicationResponse(BaseModel):
    id: str
    scholarship_id: str
    scholarship_name: str
    provider: str
    application_deadline: date | None
    scholarship_status: str
    official_application_url: str | None
    official_info_url: str
    status: str
    notes: str | None
    updated_by_user_at: datetime
    created_at: datetime
    is_user_maintained: bool = True


class NotificationResponse(BaseModel):
    id: str
    scholarship_id: str | None
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
