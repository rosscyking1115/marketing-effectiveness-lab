from __future__ import annotations

from marketing_effectiveness_lab.budget import (
    allocation_from_shares,
    current_weekly_spend,
    evaluate_budget_scenario,
    roi_weighted_allocation,
)
from marketing_effectiveness_lab.calibration import assess_lift_test_evidence, demo_lift_test_calibrations
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.governance import _gbp, assess_recommendation_readiness
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model


def test_gbp_formats_negative_values_with_abbreviation() -> None:
    assert _gbp(-2_500_000) == "-GBP 2.5M"
    assert _gbp(-12_400) == "-GBP 12K"
    assert _gbp(-300) == "-GBP 300"
    assert _gbp(2_500_000) == "GBP 2.5M"
    assert _gbp(0) == "GBP 0"


def test_recommendation_readiness_can_be_candidate_for_review() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    proposed = roi_weighted_allocation(current, mmm_result, sum(current.values()), tilt_strength=0.6)
    scenario = evaluate_budget_scenario(df, mmm_result, proposed, lookback_weeks=13)
    evidence = assess_lift_test_evidence(demo_lift_test_calibrations(mmm_result))

    readiness = assess_recommendation_readiness(
        mmm_result,
        scenario,
        weekly_rows=len(df),
        evidence_quality=evidence,
    )

    assert readiness.status == "Candidate for stakeholder review"
    assert readiness.score >= 80
    assert set(readiness.checks["status"]).issubset({"Pass", "Review"})


def test_recommendation_readiness_blocks_negative_profit_scenario() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    proposed = allocation_from_shares(current, {column: 1.0 for column in current}, 0.0)
    scenario = evaluate_budget_scenario(df, mmm_result, proposed, lookback_weeks=13)
    evidence = assess_lift_test_evidence(demo_lift_test_calibrations(mmm_result))

    readiness = assess_recommendation_readiness(
        mmm_result,
        scenario,
        weekly_rows=len(df),
        evidence_quality=evidence,
    )

    assert readiness.status == "Do not advance"
    assert "Profit impact" in readiness.checks.loc[
        readiness.checks["status"] == "Block",
        "check",
    ].tolist()
    assert readiness.required_actions


def test_recommendation_readiness_reviews_missing_evidence() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    scenario = evaluate_budget_scenario(df, mmm_result, current, lookback_weeks=13)

    readiness = assess_recommendation_readiness(
        mmm_result,
        scenario,
        weekly_rows=len(df),
        evidence_quality=None,
    )

    assert readiness.status != "Candidate for stakeholder review"
    assert "Experiment evidence" in readiness.checks.loc[
        readiness.checks["status"] == "Review",
        "check",
    ].tolist()
