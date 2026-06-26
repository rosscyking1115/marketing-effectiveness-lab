from __future__ import annotations

from marketing_effectiveness_lab.customer import (
    acquisition_channel_quality,
    cohort_retention,
    new_vs_returning_summary,
    prepare_customer_tables,
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
