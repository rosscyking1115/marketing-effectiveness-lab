"""Tests that fail when a metric-bearing path stops computing.

Most of this suite checks that code *runs* and returns the right shape. A sabotage
sweep exposed the gap: freeze the analytics functions so they return constants of
the right shape and dtype, and 121 of 139 tests still pass. Shape, range and
ordering assertions are all satisfied by a constant.

Every test here is written so that a constant or scrambled output makes it red. Two
styles are used:

* **oracle** — recompute the metric independently and require equality, so a made-up
  number cannot match;
* **sensitivity** — perturb an input and require the output to move, so an output
  that ignores its input cannot pass.

If you add a metric-bearing function, add a test here too. To check that a test in
this file really bites, monkeypatch the function it covers to return a constant and
confirm the test goes red — that is the property being asserted, not a nice-to-have.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from marketing_effectiveness_lab.analytics import (
    channel_summary,
    prepare_weekly_frame,
    spend_columns,
    summarize_kpis,
)
from marketing_effectiveness_lab.budget import (
    current_weekly_spend,
    evaluate_budget_scenario,
    optimize_budget_allocation,
)
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import (
    fit_mmm_foundation_model,
    hill_saturation,
    make_mmm_frame,
)
from marketing_effectiveness_lab.modeling import fit_baseline_model
from marketing_effectiveness_lab.uncertainty import simulate_mmm_uncertainty


@pytest.fixture(scope="module")
def demo_frame() -> pd.DataFrame:
    df, _ = generate_weekly_demo_data(seed=42)
    return df


@pytest.fixture(scope="module")
def fitted_mmm(demo_frame: pd.DataFrame):
    return fit_mmm_foundation_model(demo_frame, holdout_weeks=26)


# --------------------------------------------------------------------------------------
# analytics
# --------------------------------------------------------------------------------------


def test_summarize_kpis_matches_independently_computed_totals(demo_frame: pd.DataFrame) -> None:
    """Oracle: every KPI must equal the value recomputed straight from the frame."""

    prepared = prepare_weekly_frame(demo_frame)
    kpis = summarize_kpis(prepared)

    expected_revenue = float(prepared["revenue_gbp"].sum())
    expected_spend = float(prepared[spend_columns(prepared)].sum().sum())
    expected_orders = int(prepared["orders"].sum())

    assert kpis.revenue_gbp == pytest.approx(expected_revenue)
    assert kpis.media_spend_gbp == pytest.approx(expected_spend)
    assert kpis.orders == expected_orders
    assert kpis.new_customers == int(prepared["new_customers"].sum())
    assert kpis.average_order_value_gbp == pytest.approx(expected_revenue / expected_orders)
    assert kpis.blended_roas == pytest.approx(expected_revenue / expected_spend)
    # A constant stub would satisfy "> 0" but not the magnitudes above.
    assert kpis.revenue_gbp > 1_000_000


def test_summarize_kpis_responds_to_the_data(demo_frame: pd.DataFrame) -> None:
    """Sensitivity: doubling revenue must double the revenue KPI and the ROAS."""

    prepared = prepare_weekly_frame(demo_frame)
    doubled = prepared.copy()
    doubled["revenue_gbp"] = doubled["revenue_gbp"] * 2

    base = summarize_kpis(prepared)
    after = summarize_kpis(doubled)

    assert after.revenue_gbp == pytest.approx(base.revenue_gbp * 2)
    assert after.blended_roas == pytest.approx(base.blended_roas * 2)
    assert after.media_spend_gbp == pytest.approx(base.media_spend_gbp)


def test_channel_summary_values_track_the_underlying_spend(demo_frame: pd.DataFrame) -> None:
    """Oracle: per-channel spend, share and correlation must match direct computation."""

    prepared = prepare_weekly_frame(demo_frame)
    summary = channel_summary(prepared).set_index("channel")

    total_spend = float(prepared[spend_columns(prepared)].sum().sum())
    for column in spend_columns(prepared):
        label = {
            "paid_search_spend_gbp": "Paid search",
            "paid_social_spend_gbp": "Paid social",
            "display_spend_gbp": "Display",
            "affiliates_spend_gbp": "Affiliates",
            "email_spend_gbp": "Email",
            "influencer_spend_gbp": "Influencer",
        }[column]
        expected_spend = float(prepared[column].sum())
        # numpy rather than pandas, so the oracle does not reuse the implementation's own call.
        expected_corr = float(
            np.corrcoef(prepared[column].to_numpy(float), prepared["revenue_gbp"].to_numpy(float))[0, 1]
        )
        assert summary.loc[label, "spend_gbp"] == pytest.approx(expected_spend)
        assert summary.loc[label, "spend_share"] == pytest.approx(expected_spend / total_spend)
        assert summary.loc[label, "avg_weekly_spend_gbp"] == pytest.approx(float(prepared[column].mean()))
        assert summary.loc[label, "corr_with_revenue"] == pytest.approx(expected_corr, abs=1e-9)

    assert summary["spend_share"].sum() == pytest.approx(1.0)
    # Channels must be distinguishable; a constant table collapses this to zero.
    assert summary["spend_gbp"].nunique() == len(summary)


# --------------------------------------------------------------------------------------
# MMM transforms and fit
# --------------------------------------------------------------------------------------


def test_hill_saturation_responds_to_spend_and_half_saturation() -> None:
    """The existing bounds/monotonicity test passes on a constant; this one cannot.

    A constant array is trivially "sorted" and trivially within [0, 1], so
    ``test_hill_saturation_is_bounded_and_monotonic`` survives a frozen curve. Strict
    increases and a response to half-saturation do not.
    """

    values = np.array([10.0, 50.0, 100.0, 200.0, 400.0])
    transformed = hill_saturation(values, half_saturation=100.0, slope=1.5)

    assert np.all(np.diff(transformed) > 0), "saturation must strictly increase with spend"
    # The half-saturation point is where the curve reaches 0.5 by definition.
    assert hill_saturation(np.array([100.0]), half_saturation=100.0, slope=1.5)[0] == pytest.approx(0.5)
    # A larger half-saturation means the same spend saturates less.
    patient = hill_saturation(values, half_saturation=400.0, slope=1.5)
    assert np.all(patient < transformed)


def test_mmm_media_features_vary_with_spend(demo_frame: pd.DataFrame) -> None:
    """Sensitivity: transformed media features must move with the spend that drives them."""

    frame = make_mmm_frame(demo_frame)
    for column in spend_columns(demo_frame):
        feature = frame[f"{column}_mmm"]
        assert feature.std() > 0, f"{column} transformed feature is constant"
        correlation = float(np.corrcoef(feature.to_numpy(float), frame[column].to_numpy(float))[0, 1])
        assert correlation > 0.5, f"{column} transformed feature does not track its spend"


def test_mmm_predictions_track_actual_revenue(fitted_mmm) -> None:
    """Sensitivity: fitted predictions must correlate with the revenue they predict."""

    train = fitted_mmm.train_frame
    correlation = float(
        np.corrcoef(
            train["predicted_revenue_gbp"].to_numpy(float),
            train["revenue_gbp"].to_numpy(float),
        )[0, 1]
    )
    assert correlation > 0.8
    assert train["predicted_revenue_gbp"].std() > 0


def test_mmm_holdout_error_degrades_when_the_target_is_scrambled(demo_frame: pd.DataFrame) -> None:
    """Sensitivity: destroying the signal must make the reported holdout error worse.

    This is the sabotage committed as a test. If holdout MAPE is indifferent to whether
    revenue is real or shuffled, it is not measuring fit.
    """

    honest = fit_mmm_foundation_model(demo_frame, holdout_weeks=26)

    scrambled_frame = demo_frame.copy()
    rng = np.random.default_rng(0)
    scrambled_frame["revenue_gbp"] = rng.permutation(scrambled_frame["revenue_gbp"].to_numpy())
    scrambled = fit_mmm_foundation_model(scrambled_frame, holdout_weeks=26)

    assert honest.metrics["test_mape"] < scrambled.metrics["test_mape"]
    assert honest.metrics["train_r_squared"] > scrambled.metrics["train_r_squared"]


def test_mmm_contribution_distinguishes_channels(fitted_mmm) -> None:
    """A frozen contribution table gives every channel the same ROI; a real one does not."""

    table = fitted_mmm.contribution_table
    # Not "all six distinct": _contribution_table clamps negative coefficients to zero, and
    # the collinear channels (affiliates, email) are genuinely crushed to 0.0 ROI — see
    # docs/validation.md section 2. The property that must hold is that the table separates
    # channels at all, which a frozen table collapsing to one value cannot do.
    assert table["estimated_roi"].nunique() > 1
    assert table["estimated_roi"].std() > 0
    assert table["estimated_contribution_gbp"].std() > 0
    assert table["contribution_share"].sum() == pytest.approx(1.0)
    # Contribution must be consistent with the spend and ROI reported beside it.
    recomputed = table["estimated_contribution_gbp"] / table["spend_gbp"]
    assert np.allclose(recomputed.to_numpy(float), table["estimated_roi"].to_numpy(float))


# --------------------------------------------------------------------------------------
# baseline econometrics
# --------------------------------------------------------------------------------------


def test_baseline_model_predictions_track_actual_revenue(demo_frame: pd.DataFrame) -> None:
    result = fit_baseline_model(demo_frame, holdout_weeks=26)
    train = result.train_frame

    correlation = float(
        np.corrcoef(
            train["predicted_revenue_gbp"].to_numpy(float),
            train["revenue_gbp"].to_numpy(float),
        )[0, 1]
    )
    assert correlation > 0.8
    assert result.coefficient_table["coefficient"].std() > 0


# --------------------------------------------------------------------------------------
# budget
# --------------------------------------------------------------------------------------


def test_budget_scenario_responds_to_a_spend_increase(demo_frame: pd.DataFrame, fitted_mmm) -> None:
    """Sensitivity: spending more must change spend, contribution and profit together."""

    current = current_weekly_spend(demo_frame, lookback_weeks=13)
    increased = {channel: spend * 1.25 for channel, spend in current.items()}

    scenario = evaluate_budget_scenario(demo_frame, fitted_mmm, increased, lookback_weeks=13)

    assert scenario.summary["weekly_spend_change_gbp"] > 0
    assert scenario.summary["weekly_contribution_change_gbp"] > 0
    # Diminishing returns: a 25% spend rise must not buy a 25% contribution rise.
    spend_ratio = sum(increased.values()) / sum(current.values())
    contribution_ratio = 1 + (
        scenario.summary["weekly_contribution_change_gbp"]
        / (scenario.summary["proposed_weekly_contribution_gbp"] - scenario.summary["weekly_contribution_change_gbp"])
    )
    assert contribution_ratio < spend_ratio
    assert scenario.channel_table["weekly_spend_change_gbp"].std() > 0


def test_budget_optimizer_allocation_responds_to_its_constraints(
    demo_frame: pd.DataFrame, fitted_mmm
) -> None:
    """Sensitivity: a tighter cap must produce a different, cap-respecting allocation."""

    current = current_weekly_spend(demo_frame, lookback_weeks=13)
    total = sum(current.values())

    loose = optimize_budget_allocation(
        current, fitted_mmm, total, objective="contribution", min_share=0.02, max_share=0.50, steps=120
    )
    tight = optimize_budget_allocation(
        current, fitted_mmm, total, objective="contribution", min_share=0.02, max_share=0.20, steps=120
    )

    assert (tight.diagnostics["optimized_share"] <= 0.20 + 1e-6).all()
    assert loose.diagnostics["optimized_share"].max() > 0.20 + 1e-6, "loose cap should bind less"
    assert loose.allocation != tight.allocation
    # The optimiser must actually move budget rather than echo the current mix.
    assert any(
        abs(loose.allocation[channel] - current[channel]) > 1.0 for channel in current
    ), "optimiser returned the current mix unchanged"


# --------------------------------------------------------------------------------------
# uncertainty
# --------------------------------------------------------------------------------------


def test_uncertainty_intervals_have_width_and_vary_by_channel(fitted_mmm) -> None:
    """Ordered bounds pass on constants; positive, channel-varying widths do not."""

    result = simulate_mmm_uncertainty(fitted_mmm, draws=200, seed=42)
    contribution = result.contribution_intervals

    width = contribution["contribution_upper_gbp"] - contribution["contribution_lower_gbp"]
    assert (width > 0).all(), "every channel needs a non-degenerate interval"
    assert width.nunique() == len(width), "channels must not share an identical interval"
    assert (
        (contribution["contribution_lower_gbp"] <= contribution["contribution_mean_gbp"])
        & (contribution["contribution_mean_gbp"] <= contribution["contribution_upper_gbp"])
    ).all()

    prediction = result.prediction_intervals
    assert (prediction["prediction_upper_gbp"] - prediction["prediction_lower_gbp"] > 0).all()
    assert prediction["prediction_mean_gbp"].std() > 0


def test_uncertainty_intervals_widen_with_the_requested_level(fitted_mmm) -> None:
    """Sensitivity: a 95% interval must be strictly wider than a 50% one."""

    narrow = simulate_mmm_uncertainty(fitted_mmm, draws=400, seed=11, interval_width=0.50)
    wide = simulate_mmm_uncertainty(fitted_mmm, draws=400, seed=11, interval_width=0.95)

    narrow_width = (
        narrow.contribution_intervals["contribution_upper_gbp"]
        - narrow.contribution_intervals["contribution_lower_gbp"]
    )
    wide_width = (
        wide.contribution_intervals["contribution_upper_gbp"]
        - wide.contribution_intervals["contribution_lower_gbp"]
    )
    assert (wide_width > narrow_width).all()
