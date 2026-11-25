from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

AllowedField = Literal[
    "nationality",
    "state_ut",
    "study_scope_preference",
    "preferred_destination_countries",
    "target_university",
    "english_proficiency_test",
    "work_experience_years",
    "education_level",
    "course_field",
    "current_year_or_grade",
    "institution_type",
    "academic_score",
    "class12_board_percentile",
    "annual_family_income_inr",
    "category",
    "gender",
    "disability_percentage",
    "is_single_girl_child",
    "is_orphan_or_martyr_ward",
    "age_years",
    "study_mode",
    "receiving_other_scholarship",
]

Operator = Literal[
    "eq",
    "neq",
    "in",
    "not_in",
    "min",
    "max",
    "range",
    "bool",
    "contains_any",
    "academic_min_percentage",
]


class RuleCriterion(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=200)
    field: AllowedField | None = None
    operator: Operator | None = None
    value: Any = None
    min_cgpa_10: float | None = None
    description: str = Field(..., min_length=1, max_length=500)
    mandatory: bool = True
    source_reference: str | None = Field(default=None, max_length=500)
    any_of: list[RuleCriterion] | None = None
    all_of: list[RuleCriterion] | None = None

    @model_validator(mode="after")
    def validate_structure(self) -> RuleCriterion:
        has_leaf = self.field is not None and self.operator is not None
        has_group = bool(self.any_of) or bool(self.all_of)
        if not has_leaf and not has_group:
            raise ValueError(
                "RuleCriterion must define either (field + operator) or a non-empty any_of/all_of group."
            )
        if has_leaf and has_group:
            raise ValueError("RuleCriterion cannot mix leaf (field+operator) with any_of/all_of.")
        if self.any_of and self.all_of:
            raise ValueError("RuleCriterion cannot specify both any_of and all_of.")
        if has_leaf:
            if self.operator in ("in", "not_in", "contains_any"):
                if not isinstance(self.value, list) or len(self.value) == 0:
                    raise ValueError(f"Operator '{self.operator}' requires a non-empty list value.")
            elif self.operator == "range":
                if (
                    not isinstance(self.value, list)
                    or len(self.value) != 2
                    or not all(isinstance(x, (int, float)) for x in self.value)
                    or self.value[0] > self.value[1]
                ):
                    raise ValueError("Operator 'range' requires [min, max] with min <= max.")
            elif self.operator in ("min", "max", "academic_min_percentage"):
                if not isinstance(self.value, (int, float)):
                    raise ValueError(f"Operator '{self.operator}' requires a numeric value.")
            elif self.operator == "bool":
                if not isinstance(self.value, bool):
                    raise ValueError("Operator 'bool' requires a boolean value.")
            elif self.operator in ("eq", "neq"):
                if self.value is None:
                    raise ValueError(f"Operator '{self.operator}' requires a non-null value.")
        return self


class RuleSet(BaseModel):
    version: int = 1
    notes: str | None = None
    criteria: list[RuleCriterion] = Field(default_factory=list)


RuleCriterion.model_rebuild()
