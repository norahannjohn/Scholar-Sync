from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from app.eligibility.rules_schema import RuleCriterion, RuleSet

CriterionStatus = Literal["PASS", "FAIL", "UNKNOWN"]
OverallStatus = Literal["POTENTIAL_MATCH", "NOT_ELIGIBLE", "NEEDS_MORE_INFORMATION"]

FIELD_LABELS: dict[str, str] = {
    "nationality": "Nationality / Citizenship",
    "state_ut": "State / Union Territory of residence",
    "study_scope_preference": "Study location preference (India / Abroad / Both)",
    "preferred_destination_countries": "Preferred destination countries",
    "target_university": "Target host university",
    "english_proficiency_test": "English / language proficiency test",
    "work_experience_years": "Work experience (years)",
    "education_level": "Current / target education level",
    "course_field": "Course or field of study",
    "current_year_or_grade": "Current year or grade",
    "institution_type": "Institution type",
    "academic_score": "Academic performance",
    "class12_board_percentile": "Class XII board percentile",
    "annual_family_income_inr": "Annual family income (INR)",
    "category": "Category / community",
    "gender": "Gender",
    "disability_percentage": "Disability percentage",
    "is_single_girl_child": "Single girl child status",
    "is_orphan_or_martyr_ward": "Orphan / parent loss / martyr ward status",
    "age_years": "Age (years)",
    "study_mode": "Mode of study",
    "receiving_other_scholarship": "Other scholarship status",
}


@dataclass
class CriterionEvaluation:
    key: str
    criterion_name: str
    rule_description: str
    result: CriterionStatus
    mandatory: bool
    profile_value_display: str | None
    explanation: str
    source_reference: str | None


@dataclass
class EligibilityEvaluation:
    overall_status: OverallStatus
    overall_label: str
    summary: str
    criteria_results: list[CriterionEvaluation]
    passed_count: int
    failed_count: int
    unknown_count: int
    missing_fields: list[str]
    disclaimer: str


def _format_profile_value(field: str, value: Any, profile: dict[str, Any]) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else None
    if field == "annual_family_income_inr":
        return f"₹{int(value):,} / year"
    if field == "academic_score":
        scale = profile.get("grading_scale") or "unspecified scale"
        return f"{value} ({scale})"
    if field == "disability_percentage":
        return f"{value}%"
    if field == "class12_board_percentile":
        return f"{value}th percentile"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _is_missing(field: str, value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if field in ("category", "gender") and isinstance(value, str):
        if value.strip().lower() == "prefer_not_to_say":
            return True
    return False


def _eval_leaf(criterion: RuleCriterion, profile: dict[str, Any]) -> CriterionEvaluation:
    field = criterion.field
    assert field is not None and criterion.operator is not None
    raw_val = profile.get(field)

    if _is_missing(field, raw_val):
        human_field = FIELD_LABELS.get(field, field)
        return CriterionEvaluation(
            key=criterion.key,
            criterion_name=criterion.label,
            rule_description=criterion.description,
            result="UNKNOWN",
            mandatory=criterion.mandatory,
            profile_value_display=None,
            explanation=(
                f"Your {human_field.lower()} is not provided yet, so this criterion cannot be verified."
            ),
            source_reference=criterion.source_reference,
        )

    display_val = _format_profile_value(field, raw_val, profile)
    op = criterion.operator
    target = criterion.value

    if op == "academic_min_percentage":
        scale = (profile.get("grading_scale") or "").lower()
        score = float(raw_val)
        if scale == "percentage":
            passed = score >= float(target)
            msg = (
                f"Your {score:.1f}% meets the minimum {target}% requirement."
                if passed
                else f"Your {score:.1f}% is below the minimum {target}% requirement."
            )
            return CriterionEvaluation(
                key=criterion.key,
                criterion_name=criterion.label,
                rule_description=criterion.description,
                result="PASS" if passed else "FAIL",
                mandatory=criterion.mandatory,
                profile_value_display=display_val,
                explanation=msg,
                source_reference=criterion.source_reference,
            )
        if scale == "cgpa_10" and criterion.min_cgpa_10 is not None:
            passed = score >= float(criterion.min_cgpa_10)
            msg = (
                f"Your {score:.2f}/10 CGPA meets the minimum {criterion.min_cgpa_10:.2f} CGPA requirement."
                if passed
                else f"Your {score:.2f}/10 CGPA is below the minimum {criterion.min_cgpa_10:.2f} CGPA requirement."
            )
            return CriterionEvaluation(
                key=criterion.key,
                criterion_name=criterion.label,
                rule_description=criterion.description,
                result="PASS" if passed else "FAIL",
                mandatory=criterion.mandatory,
                profile_value_display=display_val,
                explanation=msg,
                source_reference=criterion.source_reference,
            )
        return CriterionEvaluation(
            key=criterion.key,
            criterion_name=criterion.label,
            rule_description=criterion.description,
            result="UNKNOWN",
            mandatory=criterion.mandatory,
            profile_value_display=display_val,
            explanation=(
                f"Your score is recorded using '{scale or 'unspecified'}', whereas this rule specifies "
                f"{target}%. Conversion varies by board/university; please verify or update your percentage."
            ),
            source_reference=criterion.source_reference,
        )

    if op == "eq":
        if isinstance(raw_val, str) and isinstance(target, str):
            passed = raw_val.strip().lower() == target.strip().lower()
        else:
            passed = raw_val == target
    elif op == "neq":
        if isinstance(raw_val, str) and isinstance(target, str):
            passed = raw_val.strip().lower() != target.strip().lower()
        else:
            passed = raw_val != target
    elif op == "in":
        normalized_targets = [
            t.strip().lower() if isinstance(t, str) else t for t in target
        ]
        if "all india" in normalized_targets and field == "state_ut":
            passed = True
        elif "all nationalities" in normalized_targets and field == "nationality":
            passed = True
        elif isinstance(raw_val, list):
            normalized_vals = [v.strip().lower() if isinstance(v, str) else v for v in raw_val]
            passed = any(v in normalized_targets for v in normalized_vals)
        elif isinstance(raw_val, str):
            passed = raw_val.strip().lower() in normalized_targets
        else:
            passed = raw_val in target
    elif op == "not_in":
        normalized_targets = [
            t.strip().lower() if isinstance(t, str) else t for t in target
        ]
        if isinstance(raw_val, str):
            passed = raw_val.strip().lower() not in normalized_targets
        else:
            passed = raw_val not in target
    elif op == "min":
        passed = float(raw_val) >= float(target)
    elif op == "max":
        passed = float(raw_val) <= float(target)
    elif op == "range":
        passed = float(target[0]) <= float(raw_val) <= float(target[1])
    elif op == "bool":
        passed = bool(raw_val) is bool(target)
    elif op == "contains_any":
        if isinstance(raw_val, list):
            text_val = " ".join(str(x).lower() for x in raw_val)
        else:
            text_val = str(raw_val).strip().lower()
        passed = any(str(item).strip().lower() in text_val for item in target)
    else:
        return CriterionEvaluation(
            key=criterion.key,
            criterion_name=criterion.label,
            rule_description=criterion.description,
            result="UNKNOWN",
            mandatory=criterion.mandatory,
            profile_value_display=display_val,
            explanation=f"Unsupported rule operator '{op}'.",
            source_reference=criterion.source_reference,
        )

    explanation = (
        f"Satisfied: your value ({display_val}) meets '{criterion.description}'."
        if passed
        else f"Not met: your value ({display_val}) does not satisfy '{criterion.description}'."
    )
    return CriterionEvaluation(
        key=criterion.key,
        criterion_name=criterion.label,
        rule_description=criterion.description,
        result="PASS" if passed else "FAIL",
        mandatory=criterion.mandatory,
        profile_value_display=display_val,
        explanation=explanation,
        source_reference=criterion.source_reference,
    )


def _eval_criterion(criterion: RuleCriterion, profile: dict[str, Any]) -> CriterionEvaluation:
    if criterion.any_of:
        sub_results = [_eval_criterion(sub, profile) for sub in criterion.any_of]
        if any(r.result == "PASS" for r in sub_results):
            passing = next(r for r in sub_results if r.result == "PASS")
            return CriterionEvaluation(
                key=criterion.key,
                criterion_name=criterion.label,
                rule_description=criterion.description,
                result="PASS",
                mandatory=criterion.mandatory,
                profile_value_display=passing.profile_value_display,
                explanation=f"Met via pathway '{passing.criterion_name}': {passing.explanation}",
                source_reference=criterion.source_reference or passing.source_reference,
            )
        if any(r.result == "UNKNOWN" for r in sub_results):
            unknowns = [r.criterion_name for r in sub_results if r.result == "UNKNOWN"]
            return CriterionEvaluation(
                key=criterion.key,
                criterion_name=criterion.label,
                rule_description=criterion.description,
                result="UNKNOWN",
                mandatory=criterion.mandatory,
                profile_value_display=None,
                explanation=f"Cannot determine yet; missing details for: {', '.join(unknowns)}.",
                source_reference=criterion.source_reference,
            )
        return CriterionEvaluation(
            key=criterion.key,
            criterion_name=criterion.label,
            rule_description=criterion.description,
            result="FAIL",
            mandatory=criterion.mandatory,
            profile_value_display=None,
            explanation=f"None of the qualifying pathways for '{criterion.label}' were satisfied.",
            source_reference=criterion.source_reference,
        )

    if criterion.all_of:
        sub_results = [_eval_criterion(sub, profile) for sub in criterion.all_of]
        if any(r.result == "FAIL" for r in sub_results):
            failing = next(r for r in sub_results if r.result == "FAIL")
            return CriterionEvaluation(
                key=criterion.key,
                criterion_name=criterion.label,
                rule_description=criterion.description,
                result="FAIL",
                mandatory=criterion.mandatory,
                profile_value_display=failing.profile_value_display,
                explanation=failing.explanation,
                source_reference=criterion.source_reference or failing.source_reference,
            )
        if any(r.result == "UNKNOWN" for r in sub_results):
            unknowns = [r.criterion_name for r in sub_results if r.result == "UNKNOWN"]
            return CriterionEvaluation(
                key=criterion.key,
                criterion_name=criterion.label,
                rule_description=criterion.description,
                result="UNKNOWN",
                mandatory=criterion.mandatory,
                profile_value_display=None,
                explanation=f"Cannot determine yet; missing details for: {', '.join(unknowns)}.",
                source_reference=criterion.source_reference,
            )
        return CriterionEvaluation(
            key=criterion.key,
            criterion_name=criterion.label,
            rule_description=criterion.description,
            result="PASS",
            mandatory=criterion.mandatory,
            profile_value_display=None,
            explanation=f"All sub-conditions for '{criterion.label}' are satisfied.",
            source_reference=criterion.source_reference,
        )

    return _eval_leaf(criterion, profile)


def _collect_missing_fields(criterion: RuleCriterion, profile: dict[str, Any], out: list[str]) -> None:
    if criterion.any_of:
        for sub in criterion.any_of:
            _collect_missing_fields(sub, profile, out)
        return
    if criterion.all_of:
        for sub in criterion.all_of:
            _collect_missing_fields(sub, profile, out)
        return
    if criterion.field and _is_missing(criterion.field, profile.get(criterion.field)):
        if criterion.field not in out:
            out.append(criterion.field)


def evaluate_eligibility(
    structured_rules: dict[str, Any] | None,
    profile_data: dict[str, Any] | None,
) -> EligibilityEvaluation:
    """Pure, deterministic eligibility evaluation. Never calls any LLM."""
    disclaimer = (
        "Preliminary check only based on details you provided and stored official rule definitions. "
        "Final eligibility and selection are determined solely by the scholarship provider's official guidelines and verification process."
    )
    profile = profile_data or {}

    if not structured_rules or not structured_rules.get("criteria"):
        return EligibilityEvaluation(
            overall_status="NEEDS_MORE_INFORMATION",
            overall_label="More information needed",
            summary="Structured rules for this scholarship are missing or incomplete; verify eligibility directly from the official guidelines.",
            criteria_results=[],
            passed_count=0,
            failed_count=0,
            unknown_count=0,
            missing_fields=[],
            disclaimer=disclaimer,
        )

    try:
        ruleset = RuleSet.model_validate(structured_rules)
    except ValidationError as exc:
        return EligibilityEvaluation(
            overall_status="NEEDS_MORE_INFORMATION",
            overall_label="More information needed",
            summary=f"Stored eligibility rule definition requires review ({exc.error_count()} validation issue(s)).",
            criteria_results=[],
            passed_count=0,
            failed_count=0,
            unknown_count=0,
            missing_fields=[],
            disclaimer=disclaimer,
        )

    results = [_eval_criterion(c, profile) for c in ruleset.criteria]
    passed_count = sum(1 for r in results if r.result == "PASS")
    failed_count = sum(1 for r in results if r.result == "FAIL")
    unknown_count = sum(1 for r in results if r.result == "UNKNOWN")

    missing_fields: list[str] = []
    for c in ruleset.criteria:
        res = next((r for r in results if r.key == c.key), None)
        if res and res.result == "UNKNOWN":
            _collect_missing_fields(c, profile, missing_fields)

    mandatory_failures = [r for r in results if r.mandatory and r.result == "FAIL"]
    mandatory_unknowns = [r for r in results if r.mandatory and r.result == "UNKNOWN"]

    if mandatory_failures:
        overall_status: OverallStatus = "NOT_ELIGIBLE"
        overall_label = "Not eligible based on the information entered"
        failed_names = ", ".join(r.criterion_name for r in mandatory_failures)
        summary = f"Does not meet mandatory criteria: {failed_names}."
    elif mandatory_unknowns:
        overall_status = "NEEDS_MORE_INFORMATION"
        overall_label = "More information needed"
        unknown_names = ", ".join(r.criterion_name for r in mandatory_unknowns)
        summary = f"No disqualifying rule failed, but more details are needed for: {unknown_names}."
    else:
        overall_status = "POTENTIAL_MATCH"
        overall_label = "Potential match"
        summary = (
            f"All {len([r for r in results if r.mandatory])} mandatory rule(s) passed based on your profile details."
        )

    return EligibilityEvaluation(
        overall_status=overall_status,
        overall_label=overall_label,
        summary=summary,
        criteria_results=results,
        passed_count=passed_count,
        failed_count=failed_count,
        unknown_count=unknown_count,
        missing_fields=missing_fields,
        disclaimer=disclaimer,
    )
