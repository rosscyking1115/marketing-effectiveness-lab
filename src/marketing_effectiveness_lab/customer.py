"""Customer, cohort, and lifecycle analytics for ecommerce growth decisions."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CustomerKpiSummary:
    total_customers: int
    ordering_customers: int
    repeat_customers: int
    repeat_purchase_rate: float
    revenue_gbp: float
    gross_margin_gbp: float
    gross_margin_rate: float
    refund_rate: float
    average_order_value_gbp: float
    contactable_rate: float


def prepare_customer_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Prepare customer demo tables for analytics."""

    prepared = {name: table.copy() for name, table in tables.items()}
    for table_name, date_columns in {
        "customers": ["acquisition_date", "first_order_date"],
        "orders": ["order_date"],
        "returns": ["return_date"],
        "crm_campaigns": ["start_date", "end_date"],
        "crm_events": ["event_date"],
        "customer_segments": ["snapshot_date"],
    }.items():
        if table_name in prepared:
            for column in date_columns:
                prepared[table_name][column] = pd.to_datetime(prepared[table_name][column])
    return prepared


def summarize_customer_kpis(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    customer_segments: pd.DataFrame,
) -> CustomerKpiSummary:
    """Summarize customer economics for the demo customer layer."""

    total_customers = int(customers["customer_id"].nunique())
    order_counts = orders.groupby("customer_id")["order_id"].nunique()
    ordering_customers = int(order_counts.index.nunique())
    repeat_customers = int((order_counts > 1).sum())
    revenue = float(orders["gross_revenue_gbp"].sum())
    margin = float(orders["gross_margin_gbp"].sum())
    refunds = float(orders["refund_gbp"].sum())
    order_count = int(len(orders))
    contactable = float(customer_segments["contactable_flag"].mean())

    return CustomerKpiSummary(
        total_customers=total_customers,
        ordering_customers=ordering_customers,
        repeat_customers=repeat_customers,
        repeat_purchase_rate=repeat_customers / ordering_customers if ordering_customers else 0.0,
        revenue_gbp=revenue,
        gross_margin_gbp=margin,
        gross_margin_rate=margin / revenue if revenue else 0.0,
        refund_rate=refunds / revenue if revenue else 0.0,
        average_order_value_gbp=revenue / order_count if order_count else 0.0,
        contactable_rate=contactable,
    )


def segment_summary(customer_segments: pd.DataFrame) -> pd.DataFrame:
    """Summarize RFM-style lifecycle and value segments."""

    grouped = (
        customer_segments.groupby(["lifecycle_segment", "value_segment"], as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            avg_recency_days=("recency_days", "mean"),
            avg_order_count=("order_count", "mean"),
            revenue_gbp=("revenue_gbp", "sum"),
            gross_margin_gbp=("gross_margin_gbp", "sum"),
            avg_discount_rate=("discount_rate", "mean"),
            avg_return_rate=("return_rate", "mean"),
            contactable_rate=("contactable_flag", "mean"),
        )
        .sort_values(["lifecycle_segment", "gross_margin_gbp"], ascending=[True, False])
    )
    grouped["gross_margin_per_customer_gbp"] = grouped["gross_margin_gbp"] / grouped["customers"]
    return grouped.reset_index(drop=True)


def acquisition_channel_quality(customers: pd.DataFrame, customer_segments: pd.DataFrame) -> pd.DataFrame:
    """Summarize customer quality by acquisition channel."""

    joined = customers.merge(customer_segments, on="customer_id", how="inner")
    grouped = (
        joined.groupby("acquisition_channel", as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            repeat_customers=("order_count", lambda values: int((values > 1).sum())),
            revenue_gbp=("revenue_gbp", "sum"),
            gross_margin_gbp=("gross_margin_gbp", "sum"),
            avg_order_count=("order_count", "mean"),
            avg_recency_days=("recency_days", "mean"),
            avg_discount_rate=("discount_rate", "mean"),
            avg_return_rate=("return_rate", "mean"),
            contactable_rate=("contactable_flag", "mean"),
        )
        .sort_values("gross_margin_gbp", ascending=False)
    )
    grouped["repeat_purchase_rate"] = grouped["repeat_customers"] / grouped["customers"]
    grouped["gross_margin_per_customer_gbp"] = grouped["gross_margin_gbp"] / grouped["customers"]
    return grouped.reset_index(drop=True)


def cohort_retention(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    *,
    max_month_number: int = 12,
) -> pd.DataFrame:
    """Return monthly acquisition cohort retention and value curves."""

    customer_cohorts = customers[["customer_id", "first_order_date"]].copy()
    customer_cohorts["cohort_month"] = customer_cohorts["first_order_date"].dt.to_period("M").dt.to_timestamp()
    cohort_sizes = customer_cohorts.groupby("cohort_month", as_index=False).agg(
        cohort_customers=("customer_id", "nunique")
    )

    order_months = orders[["customer_id", "order_date", "gross_revenue_gbp", "gross_margin_gbp"]].copy()
    order_months["order_month"] = order_months["order_date"].dt.to_period("M").dt.to_timestamp()
    cohort_orders = order_months.merge(
        customer_cohorts[["customer_id", "cohort_month"]],
        on="customer_id",
        how="inner",
    )
    cohort_orders["month_number"] = (
        (cohort_orders["order_month"].dt.year - cohort_orders["cohort_month"].dt.year) * 12
        + (cohort_orders["order_month"].dt.month - cohort_orders["cohort_month"].dt.month)
    )
    cohort_orders = cohort_orders[
        (cohort_orders["month_number"] >= 0) & (cohort_orders["month_number"] <= max_month_number)
    ]

    retention = (
        cohort_orders.groupby(["cohort_month", "month_number"], as_index=False)
        .agg(
            active_customers=("customer_id", "nunique"),
            revenue_gbp=("gross_revenue_gbp", "sum"),
            gross_margin_gbp=("gross_margin_gbp", "sum"),
        )
        .merge(cohort_sizes, on="cohort_month", how="left")
        .sort_values(["cohort_month", "month_number"])
    )
    retention["retention_rate"] = retention["active_customers"] / retention["cohort_customers"]
    retention["cumulative_revenue_gbp"] = retention.groupby("cohort_month")["revenue_gbp"].cumsum()
    retention["cumulative_gross_margin_gbp"] = retention.groupby("cohort_month")[
        "gross_margin_gbp"
    ].cumsum()
    retention["cohort_label"] = retention["cohort_month"].dt.strftime("%Y-%m")
    return retention.reset_index(drop=True)


def new_vs_returning_summary(customers: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Compare first orders with repeat orders."""

    first_order_dates = customers[["customer_id", "first_order_date"]]
    enriched = orders.merge(first_order_dates, on="customer_id", how="inner")
    enriched["customer_order_type"] = enriched["order_date"].eq(enriched["first_order_date"]).map(
        {True: "New customer orders", False: "Returning customer orders"}
    )
    return (
        enriched.groupby("customer_order_type", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            revenue_gbp=("gross_revenue_gbp", "sum"),
            gross_margin_gbp=("gross_margin_gbp", "sum"),
            discount_gbp=("discount_gbp", "sum"),
            refund_gbp=("refund_gbp", "sum"),
        )
        .sort_values("gross_margin_gbp", ascending=False)
        .reset_index(drop=True)
    )
