from __future__ import annotations

import pytest

from marketing_effectiveness_lab.budget import (
    allocation_from_shares,
    current_weekly_spend,
    evaluate_budget_scenario,
    roi_weighted_allocation,
)
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model


def test_current_weekly_spend_returns_channels() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    current = current_weekly_spend(df, lookback_weeks=13)

    assert len(current) == 6
    assert sum(current.values()) > 0


def test_evaluate_budget_scenario_current_mix_has_no_spend_change() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)

    scenario = evaluate_budget_scenario(df, mmm_result, current, lookback_weeks=13)

    assert len(scenario.channel_table) == 6
    assert abs(scenario.summary["weekly_spend_change_gbp"]) < 1e-6
    assert abs(scenario.summary["weekly_contribution_change_gbp"]) < 1e-6


def test_allocation_from_shares_preserves_total_budget() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    current = current_weekly_spend(df, lookback_weeks=13)
    total = sum(current.values()) * 1.1
    shares = {column: 1 for column in current}

    allocation = allocation_from_shares(current, shares, total)

    assert len(allocation) == 6
    assert sum(allocation.values()) == pytest.approx(total)


def test_roi_weighted_allocation_preserves_total_budget() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    total = sum(current.values())

    allocation = roi_weighted_allocation(current, mmm_result, total, tilt_strength=0.5)

    assert len(allocation) == 6
    assert sum(allocation.values()) == pytest.approx(total)


def test_evaluate_budget_scenario_rejects_missing_channel() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    current = current_weekly_spend(df, lookback_weeks=13)
    current.pop(next(iter(current)))

    with pytest.raises(ValueError, match="Missing proposed spend"):
        evaluate_budget_scenario(df, mmm_result, current, lookback_weeks=13)

