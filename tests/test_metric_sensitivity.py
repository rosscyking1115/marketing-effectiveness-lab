"""Tests that fail when a metric-bearing path stops computing.

Most of this suite checks that code *runs* and returns the right shape. A sabotage
sweep exposed the gap: freeze the analytics functions so they return constants of the
right shape and dtype, and the suite stayed green. Only 20 of 139 tests noticed a fully
frozen model; 119 did not. Freezing the three `analytics` summary functions on their own
produced zero red tests.

Every test here is written so that a constant or scrambled output makes it red. Two
styles are used:

* **oracle** — recompute the metric independently and require equality, so a made-up
  number cannot match;
* **sensitivity** — perturb an input and require the output to move, so an output that
  ignores its input cannot pass.

This file covers the paths that produce numbers a reader would quote: the analytics
summaries, the MMM transforms and fit, baseline econometrics, budget scenarios and
optimisation, and uncertainty intervals. It is not exhaustive over the package — the
`calibration`, `bayesian` and `customer` modules are covered by their own suites, and
`tests/test_customer_analytics.py` carries the equivalent guard for the CLV backtest.

If you add a metric-bearing function, add a test here and prove it bites: freeze the
function to a constant, watch your test go red, then unfreeze.
`scripts/sabotage_sweep.py` automates exactly that.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from marketing_effectiveness_lab.analytics import (
    channel_summary,
    prepare_weekly_frame,
    promotion_summary,
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

# Declared locally rather than imported, so an oracle never reuses the implementation's
# own lookup table to build its expectation.
CHANNEL_LABELS_FOR_ORACLE = {
    "paid_search_spend_gbp": "Paid search",
    "paid_social_spend_gbp": "Paid social",
    "display_spend_gbp": "Display",
    "affiliates_spend_gbp": "Affiliates",
    "email_spend_gbp": "Email",
    "influencer_spend_gbp": "Influencer",
}


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


def test_prepare_weekly_frame_derived_columns_are_computed(demo_frame: pd.DataFrame) -> None:
    """Oracle: the derived dashboard columns must match direct computation."""

    prepared = prepare_weekly_frame(demo_frame)
    expected_total = prepared[spend_columns(prepared)].sum(axis=1)

    assert np.allclose(prepared["total_media_spend_gbp"].to_numpy(float), expected_total.to_numpy(float))
    assert np.allclose(
        prepared["blended_roas"].to_numpy(float),
        (prepared["revenue_gbp"] / expected_total).to_numpy(float),
    )
    # Rolling averages: first row is itself, fourth row is the mean of the first four.
    assert prepared["revenue_4w_avg"].iloc[0] == pytest.approx(float(prepared["revenue_gbp"].iloc[0]))
    assert prepared["revenue_4w_avg"].iloc[3] == pytest.approx(float(prepared["revenue_gbp"].iloc[:4].mean()))
    assert prepared["media_spend_4w_avg"].iloc[3] == pytest.approx(float(expected_total.iloc[:4].mean()))
    assert prepared["total_media_spend_gbp"].std() > 0


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
        label = CHANNEL_LABELS_FOR_ORACLE[column]
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
    # Channels must be distinguishable; a constant table collapses this to one value.
    assert summary["spend_gbp"].nunique() == len(summary)


def test_promotion_summary_matches_independently_computed_groups(demo_frame: pd.DataFrame) -> None:
    """Oracle: promoted and non-promoted aggregates must match manual grouping."""

    prepared = prepare_weekly_frame(demo_frame)
    summary = promotion_summary(prepared).set_index("promotion_flag")

    for flag, label in [(0, "Non-promo weeks"), (1, "Promo weeks")]:
        subset = prepared[prepared["promotion_flag"] == flag]
        assert int(summary.loc[label, "weeks"]) == len(subset)
        assert summary.loc[label, "avg_revenue_gbp"] == pytest.approx(float(subset["revenue_gbp"].mean()))
        assert summary.loc[label, "avg_media_spend_gbp"] == pytest.approx(
            float(subset["total_media_spend_gbp"].mean())
        )
        assert summary.loc[label, "avg_promotion_depth_pct"] == pytest.approx(
            float(subset["promotion_depth_pct"].mean())
        )
        assert summary.loc[label, "avg_orders"] == pytest.approx(float(subset["orders"].mean()))

    # The two groups must be distinguishable; by construction promoted weeks discount more.
    assert (
        summary.loc["Promo weeks", "avg_promotion_depth_pct"]
        > summary.loc["Non-promo weeks", "avg_promotion_depth_pct"]
    )


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

    # Oracle: rebuild contribution from the fitted coefficients and the transformed feature,
    # independently of _contribution_table. A constant table cannot match this.
    indexed = table.set_index("channel")
    for column in spend_columns(fitted_mmm.feature_frame):
        coefficient = max(float(fitted_mmm.model.params.get(f"{column}_mmm", 0.0)), 0.0)
        expected = float(fitted_mmm.feature_frame[f"{column}_mmm"].sum()) * coefficient
        label = CHANNEL_LABELS_FOR_ORACLE[column]
        assert indexed.loc[label, "estimated_contribution_gbp"] == pytest.approx(expected, rel=1e-9)


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

    # Diminishing returns: a 25% spend rise must not buy a 25% contribution rise. Read the
    # current level from the summary rather than reconstructing it, so a frozen summary
    # fails on the assertion rather than dying in a divide.
    baseline_contribution = scenario.summary["current_weekly_contribution_gbp"]
    assert baseline_contribution > 0
    spend_ratio = sum(increased.values()) / sum(current.values())
    contribution_ratio = 1 + scenario.summary["weekly_contribution_change_gbp"] / baseline_contribution
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
    assert loose.allocation != tight.allocation
    # Structural rather than fit-dependent: the tighter cap must bind on more channels.
    loose_at_cap = int((loose.diagnostics["optimized_share"] >= 0.50 - 1e-6).sum())
    tight_at_cap = int((tight.diagnostics["optimized_share"] >= 0.20 - 1e-6).sum())
    assert tight_at_cap > loose_at_cap
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
    """A 95% interval must be strictly wider than a 50% one.

    Both runs share a seed and draw count, so the draw matrix is identical and this
    follows from quantile monotonicity. It is a check that ``interval_width`` is actually
    applied, not a statement about calibration — coverage is measured in
    ``docs/validation.md``.
    """

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
