from __future__ import annotations

import pytest

from marketing_effectiveness_lab.bayesian import build_prior_table, fit_bayesian_mmm
from marketing_effectiveness_lab.calibration import demo_lift_test_calibrations
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model


def test_bayesian_mmm_returns_posterior_outputs() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    result = fit_bayesian_mmm(mmm_result, draws=80, seed=42)

    assert result.posterior_coefficients.shape[0] == 80
    assert len(result.contribution_intervals) == 6
    assert len(result.prediction_intervals) == 26
    assert result.diagnostics["draw_count"] == 80
    assert 0 <= result.diagnostics["holdout_coverage"] <= 1
    assert (
        result.contribution_intervals["contribution_lower_gbp"]
        <= result.contribution_intervals["contribution_upper_gbp"]
    ).all()


def test_bayesian_posterior_is_well_conditioned() -> None:
    # Regression guard: the Normal-Inverse-Gamma sampler must whiten the design matrix
    # before inverting the posterior precision. Without it, X'X is ill-conditioned
    # (cond ~1e12) and the large-scale trend_squared coefficient drifts ~100x off the
    # OLS estimate, driving holdout predictions an order of magnitude too high and
    # collapsing interval coverage to zero.
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    result = fit_bayesian_mmm(mmm_result, draws=400, seed=42, interval_width=0.90)

    # Posterior means track the OLS fit in the well-identified directions.
    summary = result.coefficient_summary.set_index("feature")
    ols = mmm_result.model.params
    trend_sq_recovered = summary.loc["trend_squared", "posterior_mean"]
    assert trend_sq_recovered == pytest.approx(ols["trend_squared"], rel=0.5)

    # Posterior-predictive point estimates match the OLS holdout prediction, so the
    # sampler is not blowing up the large-scale trend term.
    assert result.diagnostics["holdout_mape"] < 0.15

    # Intervals are wide enough to be usable: coverage is in a sane range, not zero.
    assert 0.5 <= result.diagnostics["holdout_coverage"] <= 1.0


def test_bayesian_mmm_can_use_experiment_informed_priors() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    lift_tests = demo_lift_test_calibrations(mmm_result)

    priors = build_prior_table(mmm_result, lift_tests=lift_tests)
    result = fit_bayesian_mmm(mmm_result, lift_tests=lift_tests, draws=60, seed=7)

    assert (priors["prior_source"] == "Experiment-informed").sum() == 4
    assert result.diagnostics["experiment_informed_priors"] == 4


def test_bayesian_mmm_is_reproducible() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    first = fit_bayesian_mmm(mmm_result, draws=40, seed=99)
    second = fit_bayesian_mmm(mmm_result, draws=40, seed=99)

    assert first.contribution_intervals["contribution_mean_gbp"].tolist() == second.contribution_intervals[
        "contribution_mean_gbp"
    ].tolist()


def test_bayesian_mmm_validates_arguments() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    with pytest.raises(ValueError, match="draws must be positive"):
        fit_bayesian_mmm(mmm_result, draws=0)

    with pytest.raises(ValueError, match="interval_width"):
        fit_bayesian_mmm(mmm_result, interval_width=1.5)
