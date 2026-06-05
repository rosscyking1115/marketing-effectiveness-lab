"""Assemble validated connector exports into the weekly MMM dataset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from marketing_effectiveness_lab.data.connectors import (
    CONNECTOR_LOOKUP,
    validate_connector_csv_text,
    validate_connector_frame,
)
from marketing_effectiveness_lab.data.schema import REQUIRED_COLUMNS, validate_weekly_dataset


CONTROL_DEFAULTS = {
    "consumer_confidence_index": 0.0,
    "inflation_rate_pct": 0.0,
}


@dataclass(frozen=True)
class WeeklyAssemblyResult:
    weekly_dataset: pd.DataFrame
    source_summary: pd.DataFrame
    validation_errors: list[str]


def assemble_connector_csv_texts(
    connector_csv_texts: Mapping[str, str],
    control_defaults: Mapping[str, float] | None = None,
) -> WeeklyAssemblyResult:
    """Validate connector CSV strings and assemble a weekly MMM-ready dataset."""

    frames: dict[str, pd.DataFrame] = {}
    errors: list[str] = []
    for connector_key, csv_text in connector_csv_texts.items():
        if not csv_text.strip():
            continue
        parsed, connector_errors = validate_connector_csv_text(connector_key, csv_text)
        if connector_errors or parsed is None:
            label = CONNECTOR_LOOKUP[connector_key].label
            errors.extend([f"{label}: {error}" for error in connector_errors])
            continue
        frames[connector_key] = parsed

    if errors:
        return WeeklyAssemblyResult(
            weekly_dataset=_empty_weekly_dataset(),
            source_summary=_source_summary(frames),
            validation_errors=errors,
        )

    return assemble_weekly_dataset_from_connectors(frames, control_defaults=control_defaults)


def assemble_weekly_dataset_from_connectors(
    connector_frames: Mapping[str, pd.DataFrame],
    control_defaults: Mapping[str, float] | None = None,
) -> WeeklyAssemblyResult:
    """Aggregate connector exports into the documented weekly MMM schema.

    Shopify/ecommerce is treated as the reconciled outcome source. Other connectors
    are joined onto the Shopify weekly spine so revenue is never silently invented.
    """

    errors: list[str] = []
    valid_frames: dict[str, pd.DataFrame] = {}
    for connector_key, frame in connector_frames.items():
        if frame.empty:
            continue
        if connector_key not in CONNECTOR_LOOKUP:
            errors.append(f"Unknown connector '{connector_key}'.")
            continue
        connector_errors = validate_connector_frame(connector_key, frame)
        if connector_errors:
            label = CONNECTOR_LOOKUP[connector_key].label
            errors.extend([f"{label}: {error}" for error in connector_errors])
            continue
        valid_frames[connector_key] = _coerce_for_assembly(frame)

    summary = _source_summary(valid_frames)
    if errors:
        return WeeklyAssemblyResult(_empty_weekly_dataset(), summary, errors)

    if "shopify" not in valid_frames:
        return WeeklyAssemblyResult(
            weekly_dataset=_empty_weekly_dataset(),
            source_summary=summary,
            validation_errors=[
                "Shopify or ecommerce orders export is required as the reconciled outcome source."
            ],
        )

    controls = {**CONTROL_DEFAULTS, **(control_defaults or {})}
    weekly = _assemble_outcomes(valid_frames["shopify"])
    weekly = weekly.merge(
        _weekly_sum(valid_frames.get("google_ads"), "paid_search_spend_gbp", "cost_gbp"),
        on="week_start",
        how="left",
    )
    weekly = weekly.merge(
        _weekly_sum(valid_frames.get("meta_ads"), "paid_social_spend_gbp", "spend_gbp"),
        on="week_start",
        how="left",
    )
    weekly = weekly.merge(
        _weekly_sum(valid_frames.get("crm"), "email_spend_gbp", "cost_gbp"),
        on="week_start",
        how="left",
    )
    weekly = weekly.merge(_organic_sessions(valid_frames.get("ga4")), on="week_start", how="left")

    for column in [
        "paid_search_spend_gbp",
        "paid_social_spend_gbp",
        "email_spend_gbp",
        "organic_search_sessions",
    ]:
        weekly[column] = weekly[column].fillna(0.0)

    weekly["display_spend_gbp"] = 0.0
    weekly["affiliates_spend_gbp"] = 0.0
    weekly["influencer_spend_gbp"] = 0.0
    weekly["promotion_flag"] = (weekly["promotion_depth_pct"] >= 5).astype(int)
    weekly["holiday_flag"] = weekly["week_start"].dt.month.isin([11, 12]).astype(int)
    weekly["season_spring_summer"] = weekly["week_start"].dt.month.between(3, 8).astype(int)
    weekly["season_autumn_winter"] = (1 - weekly["season_spring_summer"]).astype(int)
    weekly["consumer_confidence_index"] = float(controls["consumer_confidence_index"])
    weekly["inflation_rate_pct"] = float(controls["inflation_rate_pct"])

    ordered_columns = [column.name for column in REQUIRED_COLUMNS]
    weekly = weekly[ordered_columns].sort_values("week_start").reset_index(drop=True)
    weekly["week_start"] = weekly["week_start"].dt.strftime("%Y-%m-%d")

    final_errors = validate_weekly_dataset(weekly)
    return WeeklyAssemblyResult(
        weekly_dataset=weekly,
        source_summary=summary,
        validation_errors=final_errors,
    )


def _assemble_outcomes(shopify: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        shopify.groupby("week_start", as_index=False)
        .agg(
            gross_sales_gbp=("gross_sales_gbp", "sum"),
            discounts_gbp=("discounts_gbp", "sum"),
            revenue_gbp=("net_sales_gbp", "sum"),
            orders=("orders", "sum"),
            new_customers=("new_customer_orders", "sum"),
        )
        .sort_values("week_start")
    )
    grouped["average_order_value_gbp"] = grouped.apply(
        lambda row: row["revenue_gbp"] / row["orders"] if row["orders"] else 0.0,
        axis=1,
    )
    grouped["promotion_depth_pct"] = grouped.apply(
        lambda row: row["discounts_gbp"] / row["gross_sales_gbp"]
        if row["gross_sales_gbp"]
        else 0.0,
        axis=1,
    ) * 100
    return grouped.drop(columns=["gross_sales_gbp", "discounts_gbp"])


def _weekly_sum(
    frame: pd.DataFrame | None,
    output_column: str,
    input_column: str,
) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame({"week_start": pd.Series(dtype="datetime64[ns]"), output_column: []})
    return (
        frame.groupby("week_start", as_index=False)[input_column]
        .sum()
        .rename(columns={input_column: output_column})
    )


def _organic_sessions(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame(
            {"week_start": pd.Series(dtype="datetime64[ns]"), "organic_search_sessions": []}
        )
    organic = frame[
        frame["session_source_medium"].astype(str).str.contains("organic", case=False, na=False)
    ]
    return (
        organic.groupby("week_start", as_index=False)["sessions"]
        .sum()
        .rename(columns={"sessions": "organic_search_sessions"})
    )


def _coerce_for_assembly(frame: pd.DataFrame) -> pd.DataFrame:
    typed = frame.copy()
    typed["week_start"] = pd.to_datetime(typed["week_start"])
    for column in typed.columns:
        if column == "week_start":
            continue
        numeric_values = pd.to_numeric(typed[column], errors="coerce")
        if not numeric_values.isna().any():
            typed[column] = numeric_values
    return typed


def _source_summary(frames: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for connector_key, frame in frames.items():
        if connector_key not in CONNECTOR_LOOKUP or frame.empty:
            continue
        weeks = pd.to_datetime(frame["week_start"])
        rows.append(
            {
                "connector": CONNECTOR_LOOKUP[connector_key].label,
                "rows": len(frame),
                "weeks": weeks.nunique(),
                "first_week": weeks.min().strftime("%Y-%m-%d"),
                "last_week": weeks.max().strftime("%Y-%m-%d"),
            }
        )
    return pd.DataFrame(rows, columns=["connector", "rows", "weeks", "first_week", "last_week"])


def _empty_weekly_dataset() -> pd.DataFrame:
    return pd.DataFrame(columns=[column.name for column in REQUIRED_COLUMNS])
