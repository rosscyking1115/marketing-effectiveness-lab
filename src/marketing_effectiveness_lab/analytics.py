"""Reusable analyst metrics for the Marketing Effectiveness Lab dashboard."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

CHANNEL_LABELS = {
    "paid_search_spend_gbp": "Paid search",
    "paid_social_spend_gbp": "Paid social",
    "display_spend_gbp": "Display",
    "affiliates_spend_gbp": "Affiliates",
    "email_spend_gbp": "Email",
    "influencer_spend_gbp": "Influencer",
}


@dataclass(frozen=True)
class KpiSummary:
    revenue_gbp: float
    media_spend_gbp: float
    orders: int
    new_customers: int
    average_order_value_gbp: float
    blended_roas: float


def spend_columns(df: pd.DataFrame) -> list[str]:
    """Return spend columns in display order."""

    return [column for column in CHANNEL_LABELS if column in df.columns]


def prepare_weekly_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare the weekly dataset for dashboarding."""

    prepared = df.copy()
    prepared["week_start"] = pd.to_datetime(prepared["week_start"])
    prepared = prepared.sort_values("week_start").reset_index(drop=True)
    prepared["total_media_spend_gbp"] = prepared[spend_columns(prepared)].sum(axis=1)
    # Weeks with zero media spend have an undefined ROAS; yield NaN rather than inf.
    prepared["blended_roas"] = prepared["revenue_gbp"] / prepared["total_media_spend_gbp"].replace(
        0, np.nan
    )
    prepared["revenue_4w_avg"] = prepared["revenue_gbp"].rolling(4, min_periods=1).mean()
    prepared["media_spend_4w_avg"] = prepared["total_media_spend_gbp"].rolling(4, min_periods=1).mean()
    return prepared


def summarize_kpis(df: pd.DataFrame) -> KpiSummary:
    """Summarize core commercial KPIs for a selected date range."""

    media_spend = float(df[spend_columns(df)].sum().sum())
    revenue = float(df["revenue_gbp"].sum())
    orders = int(df["orders"].sum())
    new_customers = int(df["new_customers"].sum())
    average_order_value = revenue / orders if orders else 0.0
    blended_roas = revenue / media_spend if media_spend else 0.0

    return KpiSummary(
        revenue_gbp=revenue,
        media_spend_gbp=media_spend,
        orders=orders,
        new_customers=new_customers,
        average_order_value_gbp=average_order_value,
        blended_roas=blended_roas,
    )


def weekly_spend_long(df: pd.DataFrame) -> pd.DataFrame:
    """Return weekly channel spend in long format."""

    long_df = df.melt(
        id_vars=["week_start"],
        value_vars=spend_columns(df),
        var_name="channel",
        value_name="spend_gbp",
    )
    long_df["channel"] = long_df["channel"].map(CHANNEL_LABELS)
    return long_df


def channel_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize spend share and simple association metrics by channel."""

    total_spend = df[spend_columns(df)].sum().sum()
    rows = []
    for column in spend_columns(df):
        spend = float(df[column].sum())
        rows.append(
            {
                "channel": CHANNEL_LABELS[column],
                "spend_gbp": spend,
                "spend_share": spend / total_spend if total_spend else 0,
                "corr_with_revenue": df[column].corr(df["revenue_gbp"]),
                "avg_weekly_spend_gbp": float(df[column].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("spend_gbp", ascending=False)


def promotion_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compare promoted and non-promoted weeks."""

    grouped = (
        df.groupby("promotion_flag", as_index=False)
        .agg(
            weeks=("week_start", "count"),
            avg_revenue_gbp=("revenue_gbp", "mean"),
            avg_media_spend_gbp=("total_media_spend_gbp", "mean"),
            avg_promotion_depth_pct=("promotion_depth_pct", "mean"),
            avg_orders=("orders", "mean"),
        )
        .replace({"promotion_flag": {0: "Non-promo weeks", 1: "Promo weeks"}})
    )
    return grouped


def mmm_readiness_checks(df: pd.DataFrame) -> list[dict[str, str]]:
    """Return basic readiness checks for MMM-style modeling."""

    checks: list[dict[str, str]] = []
    week_count = len(df)
    checks.append(
        {
            "check": "Weekly history",
            "status": "Pass" if week_count >= 104 else "Review",
            "detail": f"{week_count} weekly observations available.",
        }
    )

    missing = int(df.isna().sum().sum())
    checks.append(
        {
            "check": "Missing values",
            "status": "Pass" if missing == 0 else "Review",
            "detail": f"{missing} missing values found.",
        }
    )

    promo_weeks = int(df["promotion_flag"].sum())
    checks.append(
        {
            "check": "Promotion variation",
            "status": "Pass" if 0 < promo_weeks < week_count else "Review",
            "detail": f"{promo_weeks} promoted weeks available.",
        }
    )

    high_corr_pairs = []
    corr = df[spend_columns(df)].corr().abs()
    for idx, left in enumerate(corr.columns):
        for right in corr.columns[idx + 1 :]:
            if corr.loc[left, right] >= 0.85:
                high_corr_pairs.append(f"{CHANNEL_LABELS[left]} / {CHANNEL_LABELS[right]}")
    checks.append(
        {
            "check": "Channel collinearity",
            "status": "Review" if high_corr_pairs else "Pass",
            "detail": "; ".join(high_corr_pairs) if high_corr_pairs else "No spend pairs above 0.85 correlation.",
        }
    )

    return checks

