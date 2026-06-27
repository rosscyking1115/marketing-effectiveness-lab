"""Customer, cohort, and lifecycle analytics for ecommerce growth decisions."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
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


def crm_experiment_design(
    segment: pd.Series | dict[str, object],
    *,
    baseline_conversion_rate: float = 0.05,
    minimum_detectable_lift: float = 0.025,
    test_duration_days: int = 21,
) -> dict[str, object]:
    """Design a lightweight CRM holdout experiment for one retention segment."""

    segment_data = dict(segment)
    contactable_customers = int(segment_data["contactable_customers"])
    holdout_rate = float(segment_data["recommended_holdout_rate"])
    holdout_customers = int(round(contactable_customers * holdout_rate))
    treatment_customers = max(contactable_customers - holdout_customers, 0)
    required_per_group = _required_sample_per_group(
        baseline_conversion_rate,
        minimum_detectable_lift,
    )
    effective_sample_per_group = min(treatment_customers, holdout_customers)
    launch_readiness = _experiment_launch_readiness(
        str(segment_data["recommended_action"]),
        contactable_customers,
        effective_sample_per_group,
        required_per_group,
    )
    expected_incremental_margin_per_conversion = max(
        float(segment_data["avg_expected_future_margin_gbp"])
        - float(segment_data["max_incentive_cost_per_customer_gbp"]),
        0.0,
    )
    expected_incremental_conversions_at_mde = treatment_customers * minimum_detectable_lift

    return {
        "segment_label": (
            f"{segment_data['lapse_risk_band']} / "
            f"{segment_data['lifecycle_segment']} / "
            f"{segment_data['value_segment']}"
        ),
        "recommended_action": segment_data["recommended_action"],
        "launch_readiness": launch_readiness,
        "contactable_customers": contactable_customers,
        "treatment_customers": treatment_customers,
        "holdout_customers": holdout_customers,
        "recommended_holdout_rate": holdout_rate,
        "required_sample_per_group": required_per_group,
        "effective_sample_per_group": effective_sample_per_group,
        "baseline_conversion_rate": baseline_conversion_rate,
        "minimum_detectable_lift": minimum_detectable_lift,
        "test_duration_days": test_duration_days,
        "primary_metric": "Incremental gross margin per contacted customer",
        "success_rule": (
            "Scale only if treatment beats holdout on gross margin per customer "
            "and unsubscribe/refund guardrails remain within tolerance."
        ),
        "guardrail_metrics": "Unsubscribe rate, refund rate, discount rate, gross margin rate",
        "expected_incremental_conversions_at_mde": expected_incremental_conversions_at_mde,
        "expected_incremental_margin_at_mde_gbp": (
            expected_incremental_conversions_at_mde * expected_incremental_margin_per_conversion
        ),
    }


def crm_experiment_checklist(design: dict[str, object]) -> pd.DataFrame:
    """Return a launch checklist for a CRM holdout experiment design."""

    readiness = str(design["launch_readiness"])
    is_launchable = readiness in {"Ready to test", "Directional pilot"}
    rows = [
        (
            "Audience",
            "Lock segment definition and exclude customers in active tests",
            "Ready" if int(design["contactable_customers"]) > 0 else "Blocked",
        ),
        (
            "Randomization",
            "Assign treatment and holdout before campaign delivery",
            "Ready" if int(design["holdout_customers"]) > 0 else "Blocked",
        ),
        (
            "Measurement",
            "Use gross margin per contacted customer as the primary metric",
            "Ready",
        ),
        (
            "Guardrails",
            "Track unsubscribe rate, refunds, discount rate, and margin rate",
            "Ready",
        ),
        (
            "Decision",
            "Pre-commit to scale, retest, or suppress based on the success rule",
            "Ready" if is_launchable else "Review",
        ),
    ]
    return pd.DataFrame(rows, columns=["check_area", "requirement", "status"])


def build_crm_experiment_artifact(
    segment: pd.Series | dict[str, object],
    design: dict[str, object],
    checklist: pd.DataFrame,
) -> dict[str, object]:
    """Build a deterministic machine-readable CRM experiment artifact."""

    segment_data = dict(segment)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "artifact_type": "crm_experiment_brief",
        "segment": {
            "segment_label": str(design["segment_label"]),
            "recommended_action": str(segment_data["recommended_action"]),
            "lapse_risk_band": str(segment_data["lapse_risk_band"]),
            "lifecycle_segment": str(segment_data["lifecycle_segment"]),
            "value_segment": str(segment_data["value_segment"]),
            "customers": int(segment_data["customers"]),
            "contactable_customers": int(segment_data["contactable_customers"]),
            "contactable_rate": _round_float(segment_data["contactable_rate"], digits=6),
            "expected_future_margin_gbp": _round_float(segment_data["expected_future_margin_gbp"]),
            "risk_weighted_margin_gbp": _round_float(segment_data["risk_weighted_margin_gbp"]),
            "crm_evidence_status": str(segment_data["crm_evidence_status"]),
        },
        "experiment_design": {
            "launch_readiness": str(design["launch_readiness"]),
            "treatment_customers": int(design["treatment_customers"]),
            "holdout_customers": int(design["holdout_customers"]),
            "recommended_holdout_rate": _round_float(design["recommended_holdout_rate"], digits=6),
            "required_sample_per_group": int(design["required_sample_per_group"]),
            "effective_sample_per_group": int(design["effective_sample_per_group"]),
            "baseline_conversion_rate": _round_float(design["baseline_conversion_rate"], digits=6),
            "minimum_detectable_lift": _round_float(design["minimum_detectable_lift"], digits=6),
            "test_duration_days": int(design["test_duration_days"]),
            "primary_metric": str(design["primary_metric"]),
            "success_rule": str(design["success_rule"]),
            "guardrail_metrics": str(design["guardrail_metrics"]),
            "expected_incremental_conversions_at_mde": _round_float(
                design["expected_incremental_conversions_at_mde"],
            ),
            "expected_incremental_margin_at_mde_gbp": _round_float(
                design["expected_incremental_margin_at_mde_gbp"],
            ),
        },
        "checklist": [
            {
                "check_area": str(row["check_area"]),
                "requirement": str(row["requirement"]),
                "status": str(row["status"]),
            }
            for row in checklist.to_dict("records")
        ],
        "review_notes": [
            "This artifact is generated deterministically from the dashboard state.",
            "It is suitable for analyst review and CRM planning, not production approval.",
            "Production use should persist artifacts with authenticated approvers and audit logs.",
        ],
    }
    payload["artifact_id"] = _experiment_artifact_id(payload)
    return payload


def crm_experiment_artifact_json(artifact: dict[str, object]) -> str:
    """Serialize a CRM experiment artifact as stable pretty JSON."""

    return json.dumps(artifact, indent=2, sort_keys=True) + "\n"


def parse_crm_experiment_artifact_json(artifact_json: str) -> dict[str, object]:
    """Parse and validate a CRM experiment artifact JSON payload."""

    try:
        payload = json.loads(artifact_json)
    except json.JSONDecodeError as exc:
        msg = f"CRM experiment artifact JSON is invalid: {exc.msg}."
        raise ValueError(msg) from exc

    if not isinstance(payload, dict):
        msg = "CRM experiment artifact JSON must decode to an object."
        raise ValueError(msg)

    required_fields = [
        "schema_version",
        "artifact_type",
        "artifact_id",
        "segment",
        "experiment_design",
        "checklist",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        msg = f"CRM experiment artifact is missing required field(s): {', '.join(missing)}."
        raise ValueError(msg)

    if payload["schema_version"] != "1.0":
        msg = f"Unsupported CRM experiment artifact schema version: {payload['schema_version']}."
        raise ValueError(msg)

    if payload["artifact_type"] != "crm_experiment_brief":
        msg = f"Unsupported CRM experiment artifact type: {payload['artifact_type']}."
        raise ValueError(msg)

    if not isinstance(payload["segment"], dict) or not isinstance(payload["experiment_design"], dict):
        msg = "CRM experiment artifact segment and experiment_design must be objects."
        raise ValueError(msg)

    if not isinstance(payload["checklist"], list):
        msg = "CRM experiment artifact checklist must be a list."
        raise ValueError(msg)

    return payload


def compare_crm_experiment_artifacts(artifacts: Sequence[Mapping[str, object]]) -> pd.DataFrame:
    """Build a ranked comparison table from CRM experiment artifacts."""

    if not artifacts:
        msg = "At least one CRM experiment artifact is required for comparison."
        raise ValueError(msg)

    records = [
        _crm_artifact_comparison_record(artifact, index)
        for index, artifact in enumerate(artifacts)
    ]
    comparison = pd.DataFrame(records)
    comparison = comparison.sort_values(
        by=[
            "priority_score",
            "expected_incremental_margin_at_mde_gbp",
            "risk_weighted_margin_gbp",
            "contactable_customers",
            "recommended_holdout_rate",
        ],
        ascending=[False, False, False, False, True],
        na_position="last",
    ).reset_index(drop=True)
    comparison.insert(0, "comparison_rank", range(1, len(comparison) + 1))
    return comparison


def crm_experiment_artifact_comparison_csv(comparison: pd.DataFrame) -> str:
    """Serialize a CRM experiment artifact comparison table as CSV."""

    return comparison.to_csv(index=False)


def summarize_crm_experiment_portfolio(
    comparison: pd.DataFrame,
    *,
    top_n: int | None = None,
) -> dict[str, float | int | str]:
    """Summarize a planned portfolio of ranked CRM experiment artifacts."""

    selected = _selected_portfolio_experiments(comparison, top_n=top_n)
    contactable_customers = float(selected["contactable_customers"].sum())
    holdout_customers = float(selected["holdout_customers"].sum())
    treatment_customers = float(selected["treatment_customers"].sum())
    expected_margin = float(selected["expected_incremental_margin_at_mde_gbp"].sum())
    risk_weighted_margin = float(selected["risk_weighted_margin_gbp"].sum())
    readiness_counts = selected["launch_readiness"].value_counts()

    return {
        "experiments": int(len(selected)),
        "ready_to_test_experiments": int(readiness_counts.get("Ready to test", 0)),
        "directional_pilot_experiments": int(readiness_counts.get("Directional pilot", 0)),
        "underpowered_experiments": int(readiness_counts.get("Underpowered", 0)),
        "do_not_launch_experiments": int(readiness_counts.get("Do not launch", 0)),
        "contactable_customers": contactable_customers,
        "treatment_customers": treatment_customers,
        "holdout_customers": holdout_customers,
        "portfolio_holdout_rate": _safe_divide(holdout_customers, contactable_customers),
        "expected_incremental_margin_at_mde_gbp": expected_margin,
        "risk_weighted_margin_gbp": risk_weighted_margin,
        "average_priority_score": float(selected["priority_score"].mean()),
        "portfolio_status": _crm_portfolio_status(selected),
    }


def crm_experiment_portfolio_csv(
    comparison: pd.DataFrame,
    *,
    top_n: int | None = None,
) -> str:
    """Serialize a selected CRM experiment portfolio as CSV."""

    return _selected_portfolio_experiments(comparison, top_n=top_n).to_csv(index=False)


def assess_crm_experiment_portfolio_eligibility(
    comparison: pd.DataFrame,
    *,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Assess launch guardrails for a selected CRM experiment portfolio."""

    selected = _selected_portfolio_experiments(comparison, top_n=top_n)
    duplicate_segments = _duplicate_values(selected, "segment_label")
    shared_lifecycle_segments = _duplicate_values(selected, "lifecycle_segment")
    shared_value_segments = _duplicate_values(selected, "value_segment")
    underpowered = selected[selected["launch_readiness"].isin(["Underpowered", "Do not launch"])]
    holdout_rate = _safe_divide(
        float(selected["holdout_customers"].sum()),
        float(selected["contactable_customers"].sum()),
    )
    broad_overlap_labels = [*shared_lifecycle_segments, *shared_value_segments]
    has_broad_overlap = bool(broad_overlap_labels)

    rows = [
        {
            "check_area": "Segment uniqueness",
            "status": "Blocked" if duplicate_segments else "Ready",
            "finding": (
                f"Duplicate segment design(s): {', '.join(duplicate_segments)}"
                if duplicate_segments
                else "Selected experiments use unique segment labels."
            ),
            "affected_experiments": int(
                selected["segment_label"].isin(duplicate_segments).sum()
                if duplicate_segments
                else 0
            ),
            "recommendation": (
                "Keep one experiment per exact segment label before launch."
                if duplicate_segments
                else "No action required."
            ),
        },
        {
            "check_area": "Broad targeting overlap",
            "status": "Review" if has_broad_overlap else "Ready",
            "finding": (
                f"Shared lifecycle/value targeting: {', '.join(broad_overlap_labels)}"
                if has_broad_overlap
                else "No repeated lifecycle or value segment among selected experiments."
            ),
            "affected_experiments": int(
                selected[
                    selected["lifecycle_segment"].isin(shared_lifecycle_segments)
                    | selected["value_segment"].isin(shared_value_segments)
                ].shape[0]
                if has_broad_overlap
                else 0
            ),
            "recommendation": (
                "Add exclusion rules or a campaign priority order for shared broad segments."
                if has_broad_overlap
                else "No action required."
            ),
        },
        {
            "check_area": "Launch readiness",
            "status": (
                "Blocked"
                if (underpowered["launch_readiness"] == "Do not launch").any()
                else "Review"
                if not underpowered.empty
                else "Ready"
            ),
            "finding": (
                f"{len(underpowered):,} selected experiment(s) are underpowered or not launchable."
                if not underpowered.empty
                else "All selected experiments are launchable under current rules."
            ),
            "affected_experiments": int(len(underpowered)),
            "recommendation": (
                "Remove blocked tests or treat underpowered tests as directional pilots."
                if not underpowered.empty
                else "No action required."
            ),
        },
        {
            "check_area": "Holdout burden",
            "status": "Review" if holdout_rate > 0.25 else "Ready",
            "finding": f"Portfolio holdout rate is {holdout_rate * 100:,.1f}%.",
            "affected_experiments": int(len(selected) if holdout_rate > 0.25 else 0),
            "recommendation": (
                "Reduce portfolio size or lower holdout rates before launch."
                if holdout_rate > 0.25
                else "No action required."
            ),
        },
        {
            "check_area": "Measurement isolation",
            "status": "Review" if duplicate_segments or has_broad_overlap else "Ready",
            "finding": (
                "Some selected experiments could compete for campaign exposure."
                if duplicate_segments or has_broad_overlap
                else "Selected experiments have clean segment-level measurement isolation."
            ),
            "affected_experiments": int(
                len(selected) if duplicate_segments or has_broad_overlap else 0
            ),
            "recommendation": (
                "Define mutual exclusions, send priority, and suppression windows."
                if duplicate_segments or has_broad_overlap
                else "No action required."
            ),
        },
    ]
    return pd.DataFrame(rows)


def build_crm_experiment_audience_assignment(
    scored_customers: pd.DataFrame,
    artifact: Mapping[str, object],
) -> pd.DataFrame:
    """Build a deterministic customer-level treatment/holdout assignment export."""

    segment = _mapping_value(artifact, "segment")
    design = _mapping_value(artifact, "experiment_design")
    artifact_id = str(artifact.get("artifact_id", "uploaded_artifact"))
    segment_label = str(segment.get("segment_label", ""))

    required_columns = {
        "customer_id",
        "lapse_risk_band",
        "lifecycle_segment",
        "value_segment",
        "contactable_flag",
    }
    missing = sorted(required_columns.difference(scored_customers.columns))
    if missing:
        msg = f"Scored customers are missing required audience field(s): {', '.join(missing)}."
        raise ValueError(msg)

    matching = scored_customers[
        (scored_customers["lapse_risk_band"].astype(str) == str(segment.get("lapse_risk_band", "")))
        & (
            scored_customers["lifecycle_segment"].astype(str)
            == str(segment.get("lifecycle_segment", ""))
        )
        & (scored_customers["value_segment"].astype(str) == str(segment.get("value_segment", "")))
        & (scored_customers["contactable_flag"].astype(int) == 1)
    ].copy()

    if matching.empty:
        return pd.DataFrame(columns=_audience_assignment_columns())

    matching["assignment_score"] = matching["customer_id"].map(
        lambda customer_id: _assignment_score(artifact_id, str(customer_id))
    )
    matching = matching.sort_values(["assignment_score", "customer_id"]).reset_index(drop=True)
    matching["assignment_rank"] = range(1, len(matching) + 1)
    holdout_customers = min(int(_optional_float(design.get("holdout_customers"))), len(matching))
    matching["experiment_group"] = "treatment"
    if holdout_customers > 0:
        matching.loc[matching.index[:holdout_customers], "experiment_group"] = "holdout"
    matching["artifact_id"] = artifact_id
    matching["segment_label"] = segment_label
    matching["recommended_action"] = str(segment.get("recommended_action", ""))
    matching["preferred_channel"] = matching.apply(_preferred_contact_channel, axis=1)
    matching["eligibility_status"] = "Eligible"
    matching["exclusion_reason"] = ""

    for column in _audience_assignment_columns():
        if column not in matching:
            matching[column] = ""
    return matching[_audience_assignment_columns()].reset_index(drop=True)


def summarize_crm_experiment_audience(audience: pd.DataFrame) -> dict[str, float | int | str]:
    """Summarize a CRM experiment customer assignment export."""

    audience_customers = int(len(audience))
    treatment_customers = int((audience["experiment_group"] == "treatment").sum()) if audience_customers else 0
    holdout_customers = int((audience["experiment_group"] == "holdout").sum()) if audience_customers else 0
    email_reachable = int((audience["email_opt_in"].astype(float) == 1).sum()) if audience_customers else 0
    sms_reachable = int((audience["sms_opt_in"].astype(float) == 1).sum()) if audience_customers else 0
    if audience_customers == 0:
        status = "No eligible audience"
    elif holdout_customers == 0:
        status = "Missing holdout"
    else:
        status = "Ready to export"

    return {
        "audience_customers": audience_customers,
        "treatment_customers": treatment_customers,
        "holdout_customers": holdout_customers,
        "holdout_rate": _safe_divide(holdout_customers, audience_customers),
        "email_reachable_customers": email_reachable,
        "sms_reachable_customers": sms_reachable,
        "assignment_status": status,
    }


def crm_experiment_audience_csv(audience: pd.DataFrame) -> str:
    """Serialize a CRM experiment audience assignment export as CSV."""

    return audience.to_csv(index=False)


def build_crm_experiment_portfolio_audience_assignment(
    scored_customers: pd.DataFrame,
    artifacts: Sequence[Mapping[str, object]],
    *,
    top_n: int | None = None,
) -> pd.DataFrame:
    """Build a mutually exclusive customer assignment export for a CRM experiment portfolio."""

    if not artifacts:
        msg = "At least one CRM experiment artifact is required for portfolio audience export."
        raise ValueError(msg)

    comparison = compare_crm_experiment_artifacts(artifacts)
    selected = _selected_portfolio_experiments(comparison, top_n=top_n)
    artifacts_by_id = {
        str(artifact.get("artifact_id", f"uploaded_artifact_{index + 1}")): artifact
        for index, artifact in enumerate(artifacts)
    }
    assigned_customer_ids: set[str] = set()
    portfolio_rows: list[pd.DataFrame] = []
    candidate_customers = 0
    suppressed_customers = 0

    for experiment in selected.to_dict("records"):
        artifact_id = str(experiment["artifact_id"])
        artifact = artifacts_by_id.get(artifact_id)
        if artifact is None:
            continue

        audience = build_crm_experiment_audience_assignment(scored_customers, artifact)
        candidate_customers += len(audience)
        if audience.empty:
            continue

        already_assigned = audience["customer_id"].astype(str).isin(assigned_customer_ids)
        suppressed_customers += int(already_assigned.sum())
        assigned = audience[~already_assigned].copy()
        if assigned.empty:
            continue

        assigned["portfolio_priority"] = int(experiment["comparison_rank"])
        assigned["portfolio_assignment_status"] = "Assigned"
        assigned["portfolio_exclusion_reason"] = ""
        assigned_customer_ids.update(assigned["customer_id"].astype(str).tolist())
        portfolio_rows.append(assigned)

    if portfolio_rows:
        portfolio = pd.concat(portfolio_rows, ignore_index=True)
        portfolio = portfolio.sort_values(["portfolio_priority", "assignment_rank", "customer_id"])
    else:
        portfolio = pd.DataFrame(columns=_portfolio_audience_assignment_columns())

    for column in _portfolio_audience_assignment_columns():
        if column not in portfolio:
            portfolio[column] = ""
    portfolio = portfolio[_portfolio_audience_assignment_columns()].reset_index(drop=True)
    portfolio.attrs["candidate_customers"] = candidate_customers
    portfolio.attrs["suppressed_customers"] = suppressed_customers
    return portfolio


def summarize_crm_experiment_portfolio_audience(audience: pd.DataFrame) -> dict[str, float | int | str]:
    """Summarize a mutually exclusive CRM experiment portfolio audience export."""

    assigned_customers = int(len(audience))
    candidate_customers = int(audience.attrs.get("candidate_customers", assigned_customers))
    suppressed_customers = int(audience.attrs.get("suppressed_customers", 0))
    treatment_customers = int((audience["experiment_group"] == "treatment").sum()) if assigned_customers else 0
    holdout_customers = int((audience["experiment_group"] == "holdout").sum()) if assigned_customers else 0
    experiments = int(audience["artifact_id"].nunique()) if assigned_customers else 0
    if assigned_customers == 0:
        status = "No eligible audience"
    elif suppressed_customers > 0:
        status = "Ready with exclusions"
    else:
        status = "Ready to export"

    return {
        "experiments": experiments,
        "candidate_customers": candidate_customers,
        "assigned_customers": assigned_customers,
        "suppressed_customers": suppressed_customers,
        "suppression_rate": _safe_divide(suppressed_customers, candidate_customers),
        "treatment_customers": treatment_customers,
        "holdout_customers": holdout_customers,
        "holdout_rate": _safe_divide(holdout_customers, assigned_customers),
        "assignment_status": status,
    }


def crm_experiment_portfolio_audience_csv(audience: pd.DataFrame) -> str:
    """Serialize a CRM experiment portfolio audience assignment export as CSV."""

    return audience.to_csv(index=False)


def crm_experiment_brief_markdown(artifact: dict[str, object]) -> str:
    """Render a CRM experiment artifact as a stakeholder-readable markdown brief."""

    segment = artifact["segment"]
    design = artifact["experiment_design"]
    checklist = artifact["checklist"]
    if not isinstance(segment, dict) or not isinstance(design, dict) or not isinstance(checklist, list):
        msg = "Artifact has an invalid CRM experiment brief structure."
        raise ValueError(msg)

    lines = [
        "# CRM Experiment Brief",
        "",
        "## Segment",
        "",
        f"- Artifact ID: {artifact['artifact_id']}",
        f"- Segment: {segment['segment_label']}",
        f"- Recommended action: {segment['recommended_action']}",
        f"- Lapse-risk band: {segment['lapse_risk_band']}",
        f"- Lifecycle segment: {segment['lifecycle_segment']}",
        f"- Value segment: {segment['value_segment']}",
        f"- Contactable customers: {int(segment['contactable_customers']):,}",
        f"- Expected future margin: {_gbp(float(segment['expected_future_margin_gbp']))}",
        f"- Risk-weighted margin: {_gbp(float(segment['risk_weighted_margin_gbp']))}",
        f"- CRM evidence status: {segment['crm_evidence_status']}",
        "",
        "## Test Design",
        "",
        f"- Launch readiness: {design['launch_readiness']}",
        f"- Treatment customers: {int(design['treatment_customers']):,}",
        f"- Holdout customers: {int(design['holdout_customers']):,}",
        f"- Recommended holdout rate: {_pct(float(design['recommended_holdout_rate']))}",
        f"- Required sample per group: {int(design['required_sample_per_group']):,}",
        f"- Baseline conversion assumption: {_pct(float(design['baseline_conversion_rate']))}",
        f"- Minimum detectable lift: {_pct(float(design['minimum_detectable_lift']))}",
        f"- Test duration: {int(design['test_duration_days']):,} days",
        f"- Primary metric: {design['primary_metric']}",
        f"- Expected margin at MDE: {_gbp(float(design['expected_incremental_margin_at_mde_gbp']))}",
        "",
        "## Success Rule",
        "",
        str(design["success_rule"]),
        "",
        "## Guardrails",
        "",
        str(design["guardrail_metrics"]),
        "",
        "## Launch Checklist",
        "",
        "| Area | Requirement | Status |",
        "| --- | --- | --- |",
    ]
    for row in checklist:
        if isinstance(row, dict):
            lines.append(f"| {row['check_area']} | {row['requirement']} | {row['status']} |")

    lines.extend(
        [
            "",
            "## Review Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in artifact["review_notes"])
    return "\n".join(lines) + "\n"


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


def _required_sample_per_group(
    baseline_conversion_rate: float,
    minimum_detectable_lift: float,
) -> int:
    baseline = float(min(max(baseline_conversion_rate, 0.001), 0.95))
    lift = float(max(minimum_detectable_lift, 0.001))
    treatment = float(min(baseline + lift, 0.999))
    pooled = (baseline + treatment) / 2
    z_alpha = 1.96
    z_power = 0.84
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_power * math.sqrt(baseline * (1 - baseline) + treatment * (1 - treatment))
    ) ** 2
    return int(math.ceil(numerator / ((treatment - baseline) ** 2)))


def _experiment_launch_readiness(
    action: str,
    contactable_customers: int,
    effective_sample_per_group: int,
    required_sample_per_group: int,
) -> str:
    if action in {"Monitor", "Suppress incentive", "No contactable audience"} or contactable_customers == 0:
        return "Do not launch"
    if effective_sample_per_group >= required_sample_per_group:
        return "Ready to test"
    if effective_sample_per_group >= max(30, required_sample_per_group * 0.25):
        return "Directional pilot"
    return "Underpowered"


def _experiment_artifact_id(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _crm_artifact_comparison_record(
    artifact: Mapping[str, object],
    index: int,
) -> dict[str, object]:
    segment = _mapping_value(artifact, "segment")
    design = _mapping_value(artifact, "experiment_design")
    readiness = str(design.get("launch_readiness", ""))
    evidence_status = str(segment.get("crm_evidence_status", ""))
    priority_score = (
        _readiness_priority(readiness) * 25
        + _evidence_priority(evidence_status) * 5
        + min(_optional_float(design.get("expected_incremental_margin_at_mde_gbp")) / 1000, 10)
    )

    return {
        "artifact_id": str(artifact.get("artifact_id", f"uploaded_artifact_{index + 1}")),
        "segment_label": str(segment.get("segment_label", "")),
        "lapse_risk_band": str(segment.get("lapse_risk_band", "")),
        "lifecycle_segment": str(segment.get("lifecycle_segment", "")),
        "value_segment": str(segment.get("value_segment", "")),
        "recommended_action": str(segment.get("recommended_action", "")),
        "launch_readiness": readiness,
        "priority_score": round(float(priority_score), 2),
        "crm_evidence_status": evidence_status,
        "customers": _optional_float(segment.get("customers")),
        "contactable_customers": _optional_float(segment.get("contactable_customers")),
        "treatment_customers": _optional_float(design.get("treatment_customers")),
        "holdout_customers": _optional_float(design.get("holdout_customers")),
        "recommended_holdout_rate": _optional_float(design.get("recommended_holdout_rate")),
        "required_sample_per_group": _optional_float(design.get("required_sample_per_group")),
        "effective_sample_per_group": _optional_float(design.get("effective_sample_per_group")),
        "expected_incremental_margin_at_mde_gbp": _optional_float(
            design.get("expected_incremental_margin_at_mde_gbp")
        ),
        "expected_future_margin_gbp": _optional_float(segment.get("expected_future_margin_gbp")),
        "risk_weighted_margin_gbp": _optional_float(segment.get("risk_weighted_margin_gbp")),
        "primary_metric": str(design.get("primary_metric", "")),
    }


def _selected_portfolio_experiments(
    comparison: pd.DataFrame,
    *,
    top_n: int | None = None,
) -> pd.DataFrame:
    if comparison.empty:
        msg = "At least one ranked CRM experiment is required for portfolio planning."
        raise ValueError(msg)

    selected = comparison.sort_values("comparison_rank", ascending=True).copy()
    if top_n is not None:
        selected = selected.head(max(int(top_n), 1))
    return selected.reset_index(drop=True)


def _crm_portfolio_status(selected: pd.DataFrame) -> str:
    readiness = set(selected["launch_readiness"].astype(str))
    holdout_rate = _safe_divide(
        float(selected["holdout_customers"].sum()),
        float(selected["contactable_customers"].sum()),
    )
    expected_margin = float(selected["expected_incremental_margin_at_mde_gbp"].sum())

    if "Do not launch" in readiness or expected_margin <= 0:
        return "Review before launch"
    if "Underpowered" in readiness:
        return "Pilot queue"
    if holdout_rate > 0.25:
        return "Holdout burden review"
    if readiness.issubset({"Ready to test"}):
        return "Launch-ready portfolio"
    return "Mixed readiness"


def _duplicate_values(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame:
        return []
    counts = frame[column].dropna().astype(str).value_counts()
    return counts[counts > 1].index.tolist()


def _audience_assignment_columns() -> list[str]:
    return [
        "artifact_id",
        "segment_label",
        "recommended_action",
        "customer_id",
        "experiment_group",
        "assignment_rank",
        "assignment_score",
        "preferred_channel",
        "email_opt_in",
        "sms_opt_in",
        "lapse_risk_band",
        "lifecycle_segment",
        "value_segment",
        "lapse_risk_score",
        "expected_future_margin_gbp",
        "recency_days",
        "order_count",
        "gross_margin_gbp",
        "eligibility_status",
        "exclusion_reason",
    ]


def _portfolio_audience_assignment_columns() -> list[str]:
    return [
        "portfolio_priority",
        "portfolio_assignment_status",
        "portfolio_exclusion_reason",
        *_audience_assignment_columns(),
    ]


def _assignment_score(artifact_id: str, customer_id: str) -> int:
    digest = hashlib.sha256(f"{artifact_id}:{customer_id}".encode()).hexdigest()
    return int(digest[:12], 16)


def _preferred_contact_channel(customer: pd.Series) -> str:
    if int(customer.get("sms_opt_in", 0)) == 1:
        return "sms"
    if int(customer.get("email_opt_in", 0)) == 1:
        return "email"
    return "none"


def _mapping_value(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


def _readiness_priority(readiness: str) -> int:
    return {
        "Ready to test": 4,
        "Directional pilot": 3,
        "Underpowered": 2,
        "Do not launch": 0,
    }.get(readiness, 0)


def _evidence_priority(evidence_status: str) -> int:
    return {
        "Positive": 3,
        "Review": 2,
        "Needs more data": 1,
        "No prior test": 0,
        "Negative": -1,
    }.get(evidence_status, 0)


def _optional_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _round_float(value: object, digits: int = 2) -> float:
    return round(float(value), digits)


def _gbp(value: float) -> str:
    prefix = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{prefix}GBP {absolute / 1_000_000:,.1f}M"
    if absolute >= 1_000:
        return f"{prefix}GBP {absolute / 1_000:,.0f}K"
    return f"{prefix}GBP {absolute:,.0f}"


def _pct(value: float) -> str:
    return f"{value * 100:,.1f}%"
