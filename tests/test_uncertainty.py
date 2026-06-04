from __future__ import annotations

import pytest

from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model
from marketing_effectiveness_lab.uncertainty import simulate_mmm_uncertainty


def test_simulate_mmm_uncertainty_returns_intervals() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    result = simulate_mmm_uncertainty(mmm_result, draws=100, seed=42)

    assert result.draw_count == 100
    assert len(result.contribution_intervals) == 6
    assert len(result.prediction_intervals) == 26
    assert (
        result.contribution_intervals["contribution_lower_gbp"]
        <= result.contribution_intervals["contribution_upper_gbp"]
    ).all()
    assert (
        result.prediction_intervals["prediction_lower_gbp"]
        <= result.prediction_intervals["prediction_upper_gbp"]
    ).all()


def test_uncertainty_simulation_is_reproducible() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    first = simulate_mmm_uncertainty(mmm_result, draws=50, seed=7)
    second = simulate_mmm_uncertainty(mmm_result, draws=50, seed=7)

    assert first.contribution_intervals["contribution_mean_gbp"].tolist() == second.contribution_intervals[
        "contribution_mean_gbp"
    ].tolist()


def test_uncertainty_simulation_validates_arguments() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    with pytest.raises(ValueError, match="draws must be positive"):
        simulate_mmm_uncertainty(mmm_result, draws=0)

    with pytest.raises(ValueError, match="interval_width"):
        simulate_mmm_uncertainty(mmm_result, interval_width=1.2)

