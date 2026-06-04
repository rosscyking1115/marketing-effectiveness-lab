"""Schema checks for the weekly marketing effectiveness dataset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    description: str
    non_negative: bool = True
    required: bool = True


REQUIRED_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("week_start", "Monday date for the reporting week.", non_negative=False),
    ColumnSpec("revenue_gbp", "Weekly ecommerce revenue in GBP."),
    ColumnSpec("orders", "Weekly ecommerce orders."),
    ColumnSpec("new_customers", "Weekly first-time customers."),
    ColumnSpec("average_order_value_gbp", "Weekly average order value in GBP."),
    ColumnSpec("paid_search_spend_gbp", "Weekly paid search media spend in GBP."),
    ColumnSpec("paid_social_spend_gbp", "Weekly paid social media spend in GBP."),
    ColumnSpec("display_spend_gbp", "Weekly display media spend in GBP."),
    ColumnSpec("affiliates_spend_gbp", "Weekly affiliate channel spend in GBP."),
    ColumnSpec("email_spend_gbp", "Weekly email/CRM campaign spend in GBP."),
    ColumnSpec("influencer_spend_gbp", "Weekly influencer marketing spend in GBP."),
    ColumnSpec("organic_search_sessions", "Weekly organic search sessions."),
    ColumnSpec("promotion_depth_pct", "Average weekly promotional discount depth."),
    ColumnSpec("promotion_flag", "Whether a major promotion ran that week."),
    ColumnSpec("holiday_flag", "Whether the week contains a major UK retail holiday."),
    ColumnSpec("season_spring_summer", "Spring/summer seasonal collection flag."),
    ColumnSpec("season_autumn_winter", "Autumn/winter seasonal collection flag."),
    ColumnSpec("consumer_confidence_index", "Synthetic UK consumer confidence control.", non_negative=False),
    ColumnSpec("inflation_rate_pct", "Synthetic UK inflation control.", non_negative=False),
)

SPEND_COLUMNS = tuple(
    spec.name for spec in REQUIRED_COLUMNS if spec.name.endswith("_spend_gbp")
)


def validate_weekly_dataset(df: pd.DataFrame) -> list[str]:
    """Return validation errors for the weekly marketing dataset."""

    errors: list[str] = []
    required_names = [spec.name for spec in REQUIRED_COLUMNS if spec.required]
    missing = [name for name in required_names if name not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return errors

    parsed_dates = pd.to_datetime(df["week_start"], errors="coerce")
    if parsed_dates.isna().any():
        errors.append("week_start contains invalid dates.")
    elif not parsed_dates.dt.dayofweek.eq(0).all():
        errors.append("week_start must contain Monday week-start dates.")

    if df["week_start"].duplicated().any():
        errors.append("week_start must be unique.")

    if len(df) > 1 and not parsed_dates.sort_values().diff().dropna().eq(pd.Timedelta(days=7)).all():
        errors.append("week_start must be continuous weekly dates.")

    for spec in REQUIRED_COLUMNS:
        if df[spec.name].isna().any():
            errors.append(f"{spec.name} contains null values.")
        if spec.name != "week_start":
            numeric_values = pd.to_numeric(df[spec.name], errors="coerce")
            if numeric_values.isna().any():
                errors.append(f"{spec.name} contains non-numeric values.")
            if spec.non_negative and (numeric_values < 0).any():
                errors.append(f"{spec.name} contains negative values.")

    for flag_col in ("promotion_flag", "holiday_flag", "season_spring_summer", "season_autumn_winter"):
        bad_values = set(df[flag_col].dropna().unique()).difference({0, 1})
        if bad_values:
            errors.append(f"{flag_col} must contain only 0/1 values.")

    return errors


def schema_as_records(columns: Iterable[ColumnSpec] = REQUIRED_COLUMNS) -> list[dict[str, object]]:
    """Represent the schema as serializable records."""

    return [
        {
            "name": column.name,
            "description": column.description,
            "non_negative": column.non_negative,
            "required": column.required,
        }
        for column in columns
    ]
