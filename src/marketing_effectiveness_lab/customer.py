"""Customer, cohort, and lifecycle analytics for ecommerce growth decisions."""

from __future__ import annotations

import math
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


def crm_incrementality_summary(crm_campaigns: pd.DataFrame, crm_events: pd.DataFrame) -> pd.DataFrame:
    """Estimate CRM campaign lift and profit from target/holdout campaign events."""

    rows: list[dict[str, object]] = []
    for campaign in crm_campaigns.sort_values("start_date").to_dict("records"):
        campaign_events = crm_events[crm_events["campaign_id"] == campaign["campaign_id"]]
        target = campaign_events[campaign_events["treatment_group"] == "target"]
        holdout = campaign_events[campaign_events["treatment_group"] == "holdout"]

        target_customers = int(target["customer_id"].nunique())
        holdout_customers = int(holdout["customer_id"].nunique())
        sent_customers = int(target.loc[target["sent_flag"] == 1, "customer_id"].nunique())
        target_conversions = int(target["converted_flag"].sum())
        holdout_conversions = int(holdout["converted_flag"].sum())

        target_conversion_rate = _safe_divide(target_conversions, target_customers)
        holdout_conversion_rate = _safe_divide(holdout_conversions, holdout_customers)
        has_measurement_groups = target_customers > 0 and holdout_customers > 0
        conversion_lift = (
            target_conversion_rate - holdout_conversion_rate if has_measurement_groups else 0.0
        )
        conversion_lift_lower, conversion_lift_upper = _conversion_lift_interval(
            target_conversion_rate,
            target_customers,
            holdout_conversion_rate,
            holdout_customers,
        )

        target_margin_per_customer = _safe_divide(float(target["gross_margin_gbp"].sum()), target_customers)
        holdout_margin_per_customer = _safe_divide(
            float(holdout["gross_margin_gbp"].sum()),
            holdout_customers,
        )
        incremental_margin_per_customer_gbp = (
            target_margin_per_customer - holdout_margin_per_customer if has_measurement_groups else 0.0
        )
        incremental_conversions = conversion_lift * target_customers
        incremental_margin_gbp = incremental_margin_per_customer_gbp * target_customers
        campaign_cost_gbp = float(campaign["campaign_cost_gbp"])
        incentive_cost_gbp = sent_customers * float(campaign["incentive_cost_per_customer_gbp"])
        incremental_profit_gbp = incremental_margin_gbp - campaign_cost_gbp - incentive_cost_gbp

        rows.append(
            {
                "campaign_id": campaign["campaign_id"],
                "campaign_name": campaign["campaign_name"],
                "campaign_type": campaign["campaign_type"],
                "channel": campaign["channel"],
                "target_segment": campaign["target_segment"],
                "start_date": campaign["start_date"],
                "end_date": campaign["end_date"],
                "target_customers": target_customers,
                "holdout_customers": holdout_customers,
                "sent_customers": sent_customers,
                "target_conversion_rate": target_conversion_rate,
                "holdout_conversion_rate": holdout_conversion_rate,
                "conversion_lift": conversion_lift,
                "conversion_lift_lower": conversion_lift_lower,
                "conversion_lift_upper": conversion_lift_upper,
                "incremental_conversions": incremental_conversions,
                "target_margin_per_customer_gbp": target_margin_per_customer,
                "holdout_margin_per_customer_gbp": holdout_margin_per_customer,
                "incremental_margin_per_customer_gbp": incremental_margin_per_customer_gbp,
                "incremental_margin_gbp": incremental_margin_gbp,
                "campaign_cost_gbp": campaign_cost_gbp,
                "incentive_cost_gbp": incentive_cost_gbp,
                "incremental_profit_gbp": incremental_profit_gbp,
                "incremental_profit_per_target_customer_gbp": _safe_divide(
                    incremental_profit_gbp,
                    target_customers,
                ),
                "unsubscribe_rate": _safe_divide(int(target["unsubscribe_flag"].sum()), sent_customers),
                "evidence_status": _crm_evidence_status(
                    target_customers,
                    holdout_customers,
                    conversion_lift_lower,
                    conversion_lift_upper,
                    incremental_profit_gbp,
                ),
            }
        )

    return pd.DataFrame(rows)


def crm_incrementality_portfolio(summary: pd.DataFrame) -> dict[str, float | int]:
    """Summarize portfolio-level CRM incrementality diagnostics."""

    campaigns = int(len(summary))
    return {
        "campaigns": campaigns,
        "positive_campaigns": int((summary["evidence_status"] == "Positive").sum()),
        "review_campaigns": int(summary["evidence_status"].isin(["Review", "Needs more data"]).sum()),
        "total_incremental_profit_gbp": float(summary["incremental_profit_gbp"].sum()),
        "total_incremental_margin_gbp": float(summary["incremental_margin_gbp"].sum()),
        "average_conversion_lift": float(summary["conversion_lift"].mean()) if campaigns else 0.0,
        "weighted_conversion_lift": _safe_divide(
            float((summary["conversion_lift"] * summary["target_customers"]).sum()),
            float(summary["target_customers"].sum()),
        ),
    }


def retention_segment_action_plan(
    scored_customers: pd.DataFrame,
    crm_summary: pd.DataFrame,
    *,
    min_segment_customers: int = 20,
) -> pd.DataFrame:
    """Create a segment-level CRM retention plan from lapse risk, value, and holdout evidence."""

    segment_plan = (
        scored_customers.groupby(["lapse_risk_band", "lifecycle_segment", "value_segment"], as_index=False)
        .agg(
            customers=("customer_id", "nunique"),
            contactable_customers=("contactable_flag", "sum"),
            expected_future_margin_gbp=("expected_future_margin_gbp", "sum"),
            avg_expected_future_margin_gbp=("expected_future_margin_gbp", "mean"),
            avg_lapse_risk_score=("lapse_risk_score", "mean"),
            historical_margin_gbp=("gross_margin_gbp", "sum"),
            avg_discount_rate=("discount_rate", "mean"),
        )
        .reset_index(drop=True)
    )
    segment_plan["contactable_rate"] = segment_plan["contactable_customers"] / segment_plan["customers"]
    segment_plan["risk_weighted_margin_gbp"] = (
        segment_plan["expected_future_margin_gbp"] * segment_plan["avg_lapse_risk_score"] / 100
    )

    evidence_rows = [
        _matched_crm_evidence(row, crm_summary)
        for row in segment_plan[["lifecycle_segment", "value_segment"]].to_dict("records")
    ]
    evidence = pd.DataFrame(evidence_rows)
    segment_plan = pd.concat([segment_plan, evidence], axis=1)
    segment_plan["recommended_action"] = segment_plan.apply(
        lambda row: _retention_action(row, min_segment_customers),
        axis=1,
    )
    segment_plan["recommended_holdout_rate"] = segment_plan["recommended_action"].map(
        {
            "Scale tested CRM": 0.10,
            "Run holdout test": 0.20,
            "Retest offer before scaling": 0.25,
            "Suppress incentive": 0.00,
            "Monitor": 0.00,
            "No contactable audience": 0.00,
        }
    )
    segment_plan["testable_customers"] = (
        segment_plan["contactable_customers"] * (1 - segment_plan["recommended_holdout_rate"])
    ).round(0).astype(int)
    segment_plan["max_incentive_cost_per_customer_gbp"] = segment_plan.apply(
        _max_incentive_cost_per_customer,
        axis=1,
    )
    return segment_plan.sort_values(
        ["risk_weighted_margin_gbp", "expected_future_margin_gbp"],
        ascending=[False, False],
    ).reset_index(drop=True)


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


def _conversion_lift_interval(
    target_rate: float,
    target_customers: int,
    holdout_rate: float,
    holdout_customers: int,
) -> tuple[float, float]:
    if target_customers == 0 or holdout_customers == 0:
        return 0.0, 0.0
    standard_error = math.sqrt(
        (target_rate * (1 - target_rate) / target_customers)
        + (holdout_rate * (1 - holdout_rate) / holdout_customers)
    )
    lift = target_rate - holdout_rate
    return lift - 1.96 * standard_error, lift + 1.96 * standard_error


def _crm_evidence_status(
    target_customers: int,
    holdout_customers: int,
    conversion_lift_lower: float,
    conversion_lift_upper: float,
    incremental_profit_gbp: float,
) -> str:
    if target_customers < 100 or holdout_customers < 30:
        return "Needs more data"
    if conversion_lift_lower > 0 and incremental_profit_gbp > 0:
        return "Positive"
    if conversion_lift_upper < 0 or incremental_profit_gbp < 0:
        return "Negative"
    return "Review"


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _matched_crm_evidence(segment: dict[str, object], crm_summary: pd.DataFrame) -> dict[str, object]:
    lifecycle_segment = str(segment["lifecycle_segment"])
    value_segment = str(segment["value_segment"])
    matched = crm_summary[
        (crm_summary["target_segment"] == lifecycle_segment)
        | (crm_summary["target_segment"] == value_segment)
    ]
    if matched.empty:
        return {
            "matched_campaigns": 0,
            "crm_evidence_status": "No prior test",
            "avg_crm_conversion_lift": 0.0,
            "avg_crm_profit_per_target_customer_gbp": 0.0,
            "crm_incremental_profit_gbp": 0.0,
        }

    status_priority = {
        "Positive": 4,
        "Review": 3,
        "Needs more data": 2,
        "Negative": 1,
    }
    evidence_status = max(
        matched["evidence_status"],
        key=lambda status: status_priority.get(str(status), 0),
    )
    return {
        "matched_campaigns": int(len(matched)),
        "crm_evidence_status": str(evidence_status),
        "avg_crm_conversion_lift": float(matched["conversion_lift"].mean()),
        "avg_crm_profit_per_target_customer_gbp": float(
            matched["incremental_profit_per_target_customer_gbp"].mean()
        ),
        "crm_incremental_profit_gbp": float(matched["incremental_profit_gbp"].sum()),
    }


def _retention_action(segment: pd.Series, min_segment_customers: int) -> str:
    if int(segment["customers"]) < min_segment_customers or int(segment["contactable_customers"]) == 0:
        return "No contactable audience"

    risk_band = str(segment["lapse_risk_band"])
    value_segment = str(segment["value_segment"])
    evidence_status = str(segment["crm_evidence_status"])
    expected_margin = float(segment["expected_future_margin_gbp"])
    profit_per_target = float(segment["avg_crm_profit_per_target_customer_gbp"])
    discount_rate = float(segment["avg_discount_rate"])

    high_value_at_risk = risk_band in {"Medium", "High"} and value_segment in {"High value", "VIP"}
    low_value_high_discount = value_segment == "Low value" and risk_band == "High" and discount_rate > 0.12

    if evidence_status == "Positive" and high_value_at_risk and profit_per_target > 0:
        return "Scale tested CRM"
    if evidence_status == "Negative" and (low_value_high_discount or profit_per_target < 0):
        return "Suppress incentive"
    if evidence_status in {"Negative", "Review"} and high_value_at_risk:
        return "Retest offer before scaling"
    if risk_band in {"Medium", "High"} and expected_margin > 0:
        return "Run holdout test"
    return "Monitor"


def _max_incentive_cost_per_customer(segment: pd.Series) -> float:
    action = str(segment["recommended_action"])
    if action in {"Monitor", "Suppress incentive", "No contactable audience"}:
        return 0.0
    expected_margin = float(segment["avg_expected_future_margin_gbp"])
    if action == "Scale tested CRM":
        return round(max(min(expected_margin * 0.12, 10), 0), 2)
    if action == "Retest offer before scaling":
        return round(max(min(expected_margin * 0.08, 6), 0), 2)
    return round(max(min(expected_margin * 0.06, 5), 0), 2)
