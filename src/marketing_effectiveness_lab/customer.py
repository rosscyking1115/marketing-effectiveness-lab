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


def customer_value_windows(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    *,
    windows: tuple[int, ...] = (30, 60, 90, 180),
) -> pd.DataFrame:
    """Calculate cumulative customer value after first order for fixed day windows."""

    first_orders = customers[["customer_id", "acquisition_channel", "first_order_date"]].copy()
    enriched = orders.merge(first_orders, on="customer_id", how="inner")
    enriched["days_since_first_order"] = (
        enriched["order_date"] - enriched["first_order_date"]
    ).dt.days

    rows = first_orders.copy()
    for window in windows:
        window_orders = enriched[
            (enriched["days_since_first_order"] >= 0)
            & (enriched["days_since_first_order"] <= window)
        ]
        window_summary = window_orders.groupby("customer_id", as_index=False).agg(
            **{
                f"orders_{window}d": ("order_id", "nunique"),
                f"revenue_{window}d_gbp": ("gross_revenue_gbp", "sum"),
                f"gross_margin_{window}d_gbp": ("gross_margin_gbp", "sum"),
                f"refund_{window}d_gbp": ("refund_gbp", "sum"),
            }
        )
        rows = rows.merge(window_summary, on="customer_id", how="left")

    numeric_columns = [column for column in rows.columns if column.endswith("_gbp")]
    numeric_columns.extend([column for column in rows.columns if column.startswith("orders_")])
    rows[numeric_columns] = rows[numeric_columns].fillna(0)
    return rows


def customer_future_value_backtest(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    *,
    cutoff_date: pd.Timestamp | str,
    horizon_days: int = 180,
) -> pd.DataFrame:
    """Backtest segment-level future gross-margin baselines from a historical cutoff."""

    cutoff = pd.Timestamp(cutoff_date)
    horizon_end = cutoff + pd.Timedelta(days=horizon_days)
    features = _customer_features_as_of(customers, orders, cutoff)
    eligible = features[features["order_count"] > 0].copy()

    future_orders = orders[(orders["order_date"] > cutoff) & (orders["order_date"] <= horizon_end)]
    future_margin = future_orders.groupby("customer_id", as_index=False).agg(
        actual_future_orders=("order_id", "nunique"),
        actual_future_revenue_gbp=("gross_revenue_gbp", "sum"),
        actual_future_margin_gbp=("gross_margin_gbp", "sum"),
    )
    eligible = eligible.merge(future_margin, on="customer_id", how="left")
    for column in [
        "actual_future_orders",
        "actual_future_revenue_gbp",
        "actual_future_margin_gbp",
    ]:
        eligible[column] = eligible[column].fillna(0)

    segment_means = eligible.groupby(["lifecycle_segment", "value_segment"], as_index=False).agg(
        segment_expected_future_margin_gbp=("actual_future_margin_gbp", "mean")
    )
    scored = eligible.merge(segment_means, on=["lifecycle_segment", "value_segment"], how="left")
    scored["absolute_error_gbp"] = (
        scored["segment_expected_future_margin_gbp"] - scored["actual_future_margin_gbp"]
    ).abs()

    summary = (
        scored.groupby(["lifecycle_segment", "value_segment"], as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            avg_historical_margin_gbp=("gross_margin_gbp", "mean"),
            avg_actual_future_margin_gbp=("actual_future_margin_gbp", "mean"),
            expected_future_margin_gbp=("segment_expected_future_margin_gbp", "mean"),
            mean_absolute_error_gbp=("absolute_error_gbp", "mean"),
            repeat_rate_in_horizon=("actual_future_orders", lambda values: float((values > 0).mean())),
        )
        .sort_values("expected_future_margin_gbp", ascending=False)
        .reset_index(drop=True)
    )
    return summary


def score_customer_lapse_value(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    *,
    as_of_date: pd.Timestamp | str | None = None,
    calibration_cutoff_date: pd.Timestamp | str | None = None,
    horizon_days: int = 180,
) -> pd.DataFrame:
    """Score current customers with empirical future-margin and lapse-risk baselines."""

    current_date = pd.Timestamp(as_of_date) if as_of_date is not None else orders["order_date"].max()
    cutoff = (
        pd.Timestamp(calibration_cutoff_date)
        if calibration_cutoff_date is not None
        else current_date - pd.Timedelta(days=horizon_days)
    )
    current_features = _customer_features_as_of(customers, orders, current_date)
    calibration = customer_future_value_backtest(
        customers,
        orders,
        cutoff_date=cutoff,
        horizon_days=horizon_days,
    )
    expected_lookup = calibration[
        ["lifecycle_segment", "value_segment", "expected_future_margin_gbp"]
    ]
    scored = current_features.merge(
        expected_lookup,
        on=["lifecycle_segment", "value_segment"],
        how="left",
    )
    fallback_expected_margin = float(calibration["expected_future_margin_gbp"].mean())
    scored["expected_future_margin_gbp"] = scored["expected_future_margin_gbp"].fillna(
        fallback_expected_margin
    )
    scored["lapse_risk_score"] = scored.apply(_lapse_risk_score, axis=1)
    scored["lapse_risk_band"] = pd.cut(
        scored["lapse_risk_score"],
        bins=[-0.1, 30, 60, 100],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    scored["as_of_date"] = current_date
    scored["calibration_cutoff_date"] = cutoff
    return scored.sort_values(
        ["lapse_risk_score", "expected_future_margin_gbp"],
        ascending=[False, False],
    ).reset_index(drop=True)


def lapse_value_segment_summary(scored_customers: pd.DataFrame) -> pd.DataFrame:
    """Summarize expected future margin and lapse risk by customer segment."""

    summary = (
        scored_customers.groupby(["lapse_risk_band", "lifecycle_segment", "value_segment"], as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            expected_future_margin_gbp=("expected_future_margin_gbp", "sum"),
            avg_expected_future_margin_gbp=("expected_future_margin_gbp", "mean"),
            avg_lapse_risk_score=("lapse_risk_score", "mean"),
            historical_margin_gbp=("gross_margin_gbp", "sum"),
            contactable_rate=("contactable_flag", "mean"),
        )
        .sort_values(["lapse_risk_band", "expected_future_margin_gbp"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return summary


def _customer_features_as_of(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    historical_orders = orders[orders["order_date"] <= as_of_date]
    order_summary = historical_orders.groupby("customer_id", as_index=False).agg(
        latest_order_date=("order_date", "max"),
        order_count=("order_id", "nunique"),
        revenue_gbp=("gross_revenue_gbp", "sum"),
        discount_gbp=("discount_gbp", "sum"),
        refund_gbp=("refund_gbp", "sum"),
        gross_margin_gbp=("gross_margin_gbp", "sum"),
    )
    features = customers.merge(order_summary, on="customer_id", how="left")
    for column in [
        "order_count",
        "revenue_gbp",
        "discount_gbp",
        "refund_gbp",
        "gross_margin_gbp",
    ]:
        features[column] = features[column].fillna(0)

    latest_order = pd.to_datetime(features["latest_order_date"])
    features["recency_days"] = (as_of_date - latest_order).dt.days
    features.loc[features["latest_order_date"].isna(), "recency_days"] = 9999
    features["recency_days"] = features["recency_days"].clip(lower=0).astype(int)
    features["discount_rate"] = (
        features["discount_gbp"] / features["revenue_gbp"].where(features["revenue_gbp"] > 0)
    ).fillna(0)
    features["return_rate"] = (
        features["refund_gbp"] / features["revenue_gbp"].where(features["revenue_gbp"] > 0)
    ).fillna(0)
    features["contactable_flag"] = (
        (features["email_opt_in"] == 1) | (features["sms_opt_in"] == 1)
    ).astype(int)
    features["lifecycle_segment"] = pd.cut(
        features["recency_days"],
        bins=[-1, 30, 120, 240, 10_000],
        labels=["New", "Active", "Lapsing", "Dormant"],
    ).astype(str)
    features["value_segment"] = pd.qcut(
        features["gross_margin_gbp"].rank(method="first"),
        q=4,
        labels=["Low value", "Mid value", "High value", "VIP"],
    ).astype(str)
    return features


def _lapse_risk_score(customer: pd.Series) -> float:
    recency_component = min(float(customer["recency_days"]) / 240 * 65, 65)
    frequency_component = max(20 - float(customer["order_count"]) * 4, 0)
    value_component = {
        "Low value": 15,
        "Mid value": 9,
        "High value": 4,
        "VIP": 0,
    }[str(customer["value_segment"])]
    discount_component = min(float(customer["discount_rate"]) * 20, 8)
    score = recency_component + frequency_component + value_component + discount_component
    return round(float(min(max(score, 0), 100)), 1)
