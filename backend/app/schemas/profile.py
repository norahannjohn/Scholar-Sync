from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

EducationLevel = Literal[
    "school", "diploma", "undergraduate", "postgraduate", "doctoral", "other"
]
GradingScale = Literal["percentage", "cgpa_10", "cgpa_4", "marks"]
CategoryOption = Literal[
    "general", "obc", "sc", "st", "ews", "minority", "prefer_not_to_say"
]
GenderOption = Literal["female", "male", "non_binary", "prefer_not_to_say"]
StudyModeOption = Literal["regular", "distance", "part_time"]
StudyScopePreference = Literal["india", "abroad", "both"]


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=150)
    nationality: str | None = Field(default=None, max_length=100)
    state_ut: str | None = Field(default=None, max_length=100)
    study_scope_preference: StudyScopePreference | None = None
    preferred_destination_countries: list[str] = Field(default_factory=list)
    target_university: str | None = Field(default=None, max_length=200)
    preferred_funding_types: list[str] = Field(default_factory=list)
    english_proficiency_test: str | None = Field(default=None, max_length=80)
    work_experience_years: float | None = Field(default=None, ge=0, le=50)
    education_level: EducationLevel | None = None
    course_field: str | None = Field(default=None, max_length=150)
    current_year_or_grade: int | None = Field(default=None, ge=1, le=12)
    institution_name: str | None = Field(default=None, max_length=200)
    institution_type: str | None = Field(default=None, max_length=80)
    grading_scale: GradingScale | None = None
    academic_score: float | None = Field(default=None, ge=0, le=10000)
    class12_board_percentile: float | None = Field(default=None, ge=0, le=100)
    annual_family_income_inr: int | None = Field(default=None, ge=0, le=100_000_000)
    category: CategoryOption | None = None
    gender: GenderOption | None = None
    disability_percentage: int | None = Field(default=None, ge=0, le=100)
    is_single_girl_child: bool | None = None
    is_orphan_or_martyr_ward: bool | None = None
    age_years: int | None = Field(default=None, ge=5, le=80)
    study_mode: StudyModeOption | None = None
    receiving_other_scholarship: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)
    consent_matching: bool = True

    @model_validator(mode="after")
    def validate_score_and_scale(self) -> ProfileUpdateRequest:
        if self.academic_score is not None:
            if self.grading_scale == "percentage" and self.academic_score > 100:
                raise ValueError("Percentage score cannot exceed 100.")
            if self.grading_scale == "cgpa_10" and self.academic_score > 10:
                raise ValueError("CGPA (10-point scale) cannot exceed 10.")
            if self.grading_scale == "cgpa_4" and self.academic_score > 4:
                raise ValueError("CGPA (4-point scale) cannot exceed 4.")
        return self


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    display_name: str | None
    nationality: str | None
    state_ut: str | None
    study_scope_preference: str | None
    preferred_destination_countries: list[str]
    target_university: str | None
    preferred_funding_types: list[str]
    english_proficiency_test: str | None
    work_experience_years: float | None
    education_level: str | None
    course_field: str | None
    current_year_or_grade: int | None
    institution_name: str | None
    institution_type: str | None
    grading_scale: str | None
    academic_score: float | None
    class12_board_percentile: float | None
    annual_family_income_inr: int | None
    category: str | None
    gender: str | None
    disability_percentage: int | None
    is_single_girl_child: bool | None
    is_orphan_or_martyr_ward: bool | None
    age_years: int | None
    study_mode: str | None
    receiving_other_scholarship: bool | None
    notes: str | None
    consent_matching: bool
    completeness_fields_filled: int
    completeness_total_core: int
    updated_at: datetime

    model_config = {"from_attributes": True}
