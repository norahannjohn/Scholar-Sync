from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.eligibility.engine import evaluate_eligibility
from app.eligibility.rules_schema import RuleSet


def test_rule_schema_rejects_malformed_rules() -> None:
    with pytest.raises(ValidationError):
        RuleSet.model_validate(
            {
                "criteria": [
                    {
                        "key": "bad_range",
                        "label": "Bad range",
                        "field": "age_years",
                        "operator": "range",
                        "value": [30, 18],  # min > max
                        "description": "Invalid range",
                    }
                ]
            }
        )

    with pytest.raises(ValidationError):
        RuleSet.model_validate(
            {
                "criteria": [
                    {
                        "key": "bad_field",
                        "label": "Unknown field",
                        "field": "aadhaar_number",  # forbidden/unsupported
                        "operator": "eq",
                        "value": "123",
                        "description": "Unsupported",
                    }
                ]
            }
        )


def test_all_mandatory_pass_returns_potential_match() -> None:
    rules = {
        "version": 1,
        "criteria": [
            {
                "key": "gender",
                "label": "Female",
                "field": "gender",
                "operator": "eq",
                "value": "female",
                "description": "Female student",
                "mandatory": True,
            },
            {
                "key": "income",
                "label": "Income cap",
                "field": "annual_family_income_inr",
                "operator": "max",
                "value": 800000,
                "description": "Max 8 lakh",
                "mandatory": True,
            },
        ],
    }
    res = evaluate_eligibility(
        rules, {"gender": "female", "annual_family_income_inr": 800000}  # boundary equal
    )
    assert res.overall_status == "POTENTIAL_MATCH"
    assert res.passed_count == 2
    assert res.failed_count == 0
    assert res.unknown_count == 0


def test_income_boundary_fail_returns_not_eligible() -> None:
    rules = {
        "version": 1,
        "criteria": [
            {
                "key": "income",
                "label": "Income cap",
                "field": "annual_family_income_inr",
                "operator": "max",
                "value": 800000,
                "description": "Max 8 lakh",
                "mandatory": True,
            }
        ],
    }
    res = evaluate_eligibility(rules, {"annual_family_income_inr": 800001})
    assert res.overall_status == "NOT_ELIGIBLE"
    assert res.failed_count == 1
    assert res.criteria_results[0].result == "FAIL"


def test_missing_or_prefer_not_to_say_never_silently_passes() -> None:
    rules = {
        "version": 1,
        "criteria": [
            {
                "key": "gender",
                "label": "Female",
                "field": "gender",
                "operator": "eq",
                "value": "female",
                "description": "Female student",
                "mandatory": True,
            },
            {
                "key": "income",
                "label": "Income",
                "field": "annual_family_income_inr",
                "operator": "max",
                "value": 800000,
                "description": "Max 8 lakh",
                "mandatory": True,
            },
        ],
    }
    res = evaluate_eligibility(rules, {"gender": "prefer_not_to_say"})
    assert res.overall_status == "NEEDS_MORE_INFORMATION"
    assert res.unknown_count == 2
    assert "gender" in res.missing_fields
    assert "annual_family_income_inr" in res.missing_fields


def test_different_grading_scales_and_ambiguity() -> None:
    rules = {
        "version": 1,
        "criteria": [
            {
                "key": "merit",
                "label": "Minimum 75% / 8.0 CGPA",
                "field": "academic_score",
                "operator": "academic_min_percentage",
                "value": 75,
                "min_cgpa_10": 8.0,
                "description": "75% or 8.0 CGPA on 10-point scale",
                "mandatory": True,
            }
        ],
    }
    # Percentage passes at 75.0
    assert (
        evaluate_eligibility(
            rules, {"grading_scale": "percentage", "academic_score": 75.0}
        ).overall_status
        == "POTENTIAL_MATCH"
    )
    # CGPA 10 passes at 8.0, fails at 7.9
    assert (
        evaluate_eligibility(
            rules, {"grading_scale": "cgpa_10", "academic_score": 8.0}
        ).overall_status
        == "POTENTIAL_MATCH"
    )
    assert (
        evaluate_eligibility(
            rules, {"grading_scale": "cgpa_10", "academic_score": 7.9}
        ).overall_status
        == "NOT_ELIGIBLE"
    )
    # Marks without total is UNKNOWN, never guessed!
    marks_res = evaluate_eligibility(rules, {"grading_scale": "marks", "academic_score": 450})
    assert marks_res.overall_status == "NEEDS_MORE_INFORMATION"
    assert marks_res.criteria_results[0].result == "UNKNOWN"


def test_any_of_and_range_operators() -> None:
    rules = {
        "version": 1,
        "criteria": [
            {
                "key": "age",
                "label": "Age 17-22",
                "field": "age_years",
                "operator": "range",
                "value": [17, 22],
                "description": "Age between 17 and 22",
                "mandatory": True,
            },
            {
                "key": "pathway",
                "label": "Merit pathway",
                "description": "Top 1% Class XII OR 90% academic score",
                "mandatory": True,
                "any_of": [
                    {
                        "key": "top1",
                        "label": "Top 1% Board",
                        "field": "class12_board_percentile",
                        "operator": "min",
                        "value": 99.0,
                        "description": "99th percentile",
                    },
                    {
                        "key": "score90",
                        "label": "90% Score",
                        "field": "academic_score",
                        "operator": "academic_min_percentage",
                        "value": 90,
                        "description": "90% marks",
                    },
                ],
            },
        ],
    }
    res = evaluate_eligibility(
        rules,
        {"age_years": 18, "class12_board_percentile": 99.2},
    )
    assert res.overall_status == "POTENTIAL_MATCH"

    res_fail = evaluate_eligibility(
        rules,
        {"age_years": 23, "class12_board_percentile": 99.2},
    )
    assert res_fail.overall_status == "NOT_ELIGIBLE"


def test_missing_or_empty_rules_returns_needs_more_info() -> None:
    res = evaluate_eligibility({}, {"state_ut": "Kerala"})
    assert res.overall_status == "NEEDS_MORE_INFORMATION"
