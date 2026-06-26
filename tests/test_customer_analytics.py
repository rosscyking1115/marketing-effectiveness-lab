from __future__ import annotations

from marketing_effectiveness_lab.customer import (
    acquisition_channel_quality,
    cohort_retention,
    crm_incrementality_portfolio,
    crm_incrementality_summary,
    customer_future_value_backtest,
    customer_value_windows,
    lapse_value_segment_summary,
    new_vs_returning_summary,
    prepare_customer_tables,
    score_customer_lapse_value,
    segment_summary,
    summarize_customer_kpis,
)
from marketing_effectiveness_lab.data.customer_generator import generate_customer_demo_data


def test_customer_kpis_summarize_ecommerce_economics() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = summarize_customer_kpis(
        tables["customers"],
        tables["orders"],
        tables["customer_segments"],
    )

    assert summary.total_customers == 800
    assert summary.ordering_customers == 800
    assert summary.repeat_customers > 0
    assert 0 < summary.repeat_purchase_rate < 1
    assert summary.revenue_gbp > summary.gross_margin_gbp > 0
    assert 0 < summary.gross_margin_rate < 1
    assert 0 < summary.contactable_rate <= 1


def test_segment_summary_preserves_customer_counts() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = segment_summary(tables["customer_segments"])

    assert summary["customers"].sum() == 800
    assert summary["gross_margin_gbp"].sum() > 0
    assert summary["gross_margin_per_customer_gbp"].min() >= 0
    assert set(summary["value_segment"]) == {"Low value", "Mid value", "High value", "VIP"}


def test_acquisition_channel_quality_has_repeat_and_margin_fields() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    quality = acquisition_channel_quality(tables["customers"], tables["customer_segments"])

    assert quality["customers"].sum() == 800
    assert quality["gross_margin_per_customer_gbp"].max() > 0
    assert quality["repeat_purchase_rate"].between(0, 1).all()
    assert quality["contactable_rate"].between(0, 1).all()


def test_cohort_retention_returns_monthly_curve() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    retention = cohort_retention(tables["customers"], tables["orders"], max_month_number=6)

    assert retention["month_number"].min() == 0
    assert retention["month_number"].max() <= 6
    assert retention["retention_rate"].between(0, 1).all()
    assert retention["cumulative_gross_margin_gbp"].min() > 0
    assert retention["cohort_label"].str.len().eq(7).all()


def test_new_vs_returning_summary_splits_first_and_repeat_orders() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = new_vs_returning_summary(tables["customers"], tables["orders"])

    assert set(summary["customer_order_type"]) == {
        "New customer orders",
        "Returning customer orders",
    }
    assert summary["orders"].sum() == len(tables["orders"])
    assert summary["gross_margin_gbp"].sum() == tables["orders"]["gross_margin_gbp"].sum()


def test_customer_value_windows_are_cumulative() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    values = customer_value_windows(tables["customers"], tables["orders"])

    assert len(values) == 800
    assert values["gross_margin_30d_gbp"].le(values["gross_margin_180d_gbp"]).all()
    assert values["revenue_90d_gbp"].le(values["revenue_180d_gbp"]).all()
    assert values["orders_180d"].ge(1).all()


def test_customer_future_value_backtest_returns_segment_baseline() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    backtest = customer_future_value_backtest(
        tables["customers"],
        tables["orders"],
        cutoff_date="2025-01-01",
        horizon_days=180,
    )

    assert {"lifecycle_segment", "value_segment", "expected_future_margin_gbp"}.issubset(backtest.columns)
    assert backtest["customers"].sum() > 0
    assert backtest["expected_future_margin_gbp"].ge(0).all()
    assert backtest["mean_absolute_error_gbp"].ge(0).all()
    assert backtest["repeat_rate_in_horizon"].between(0, 1).all()


def test_score_customer_lapse_value_produces_risk_bands_and_expected_margin() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )

    assert len(scored) == 800
    assert scored["expected_future_margin_gbp"].ge(0).all()
    assert scored["lapse_risk_score"].between(0, 100).all()
    assert set(scored["lapse_risk_band"]).issubset({"Low", "Medium", "High"})
    assert scored["lapse_risk_score"].is_monotonic_decreasing


def test_lapse_value_segment_summary_preserves_customer_count() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )

    summary = lapse_value_segment_summary(scored)

    assert summary["customers"].sum() == 800
    assert summary["expected_future_margin_gbp"].sum() >= 0
    assert summary["avg_lapse_risk_score"].between(0, 100).all()
    assert summary["contactable_rate"].between(0, 1).all()


def test_crm_incrementality_summary_estimates_holdout_lift_and_profit() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())

    summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])

    assert len(summary) == len(tables["crm_campaigns"])
    assert summary["target_customers"].gt(0).all()
    assert summary["holdout_customers"].ge(0).all()
    assert summary["holdout_customers"].gt(0).any()
    assert summary["target_conversion_rate"].between(0, 1).all()
    assert summary["holdout_conversion_rate"].between(0, 1).all()
    assert summary["conversion_lift_lower"].le(summary["conversion_lift"]).all()
    assert summary["conversion_lift_upper"].ge(summary["conversion_lift"]).all()
    assert summary["unsubscribe_rate"].between(0, 1).all()
    assert set(summary["evidence_status"]).issubset(
        {"Positive", "Review", "Negative", "Needs more data"}
    )


def test_crm_incrementality_portfolio_rolls_up_campaign_diagnostics() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])

    portfolio = crm_incrementality_portfolio(summary)

    assert portfolio["campaigns"] == len(summary)
    assert portfolio["positive_campaigns"] >= 0
    assert portfolio["review_campaigns"] >= 0
    assert isinstance(portfolio["total_incremental_profit_gbp"], float)
    assert isinstance(portfolio["total_incremental_margin_gbp"], float)
