from __future__ import annotations

from pydantic import BaseModel


class CriterionEvaluationSchema(BaseModel):
    key: str
    criterion_name: str
    rule_description: str
    result: str
    mandatory: bool
    profile_value_display: str | None = None
    explanation: str
    source_reference: str | None = None


class EligibilityEvaluationSchema(BaseModel):
    overall_status: str
    overall_label: str
    summary: str
    criteria_results: list[CriterionEvaluationSchema]
    passed_count: int
    failed_count: int
    unknown_count: int
    missing_fields: list[str]
    disclaimer: str
