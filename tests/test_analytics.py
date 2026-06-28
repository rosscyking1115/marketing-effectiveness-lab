from __future__ import annotations

import numpy as np

from marketing_effectiveness_lab.analytics import (
    channel_summary,
    mmm_readiness_checks,
    prepare_weekly_frame,
    promotion_summary,
    spend_columns,
    summarize_kpis,
    weekly_spend_long,
)
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data


def test_blended_roas_is_nan_not_inf_for_zero_spend_weeks() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    df.loc[0, spend_columns(df)] = 0.0

    prepared = prepare_weekly_frame(df)

    # The zero-spend week has undefined ROAS (NaN), not inf, and only that week.
    assert prepared["blended_roas"].isna().sum() == 1
    assert not np.isinf(prepared["blended_roas"].to_numpy()).any()


def test_dashboard_metrics_are_computed() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)

    assert "total_media_spend_gbp" in prepared.columns
    assert "revenue_4w_avg" in prepared.columns
    assert kpis.revenue_gbp > 0
    assert kpis.media_spend_gbp > 0
    assert kpis.blended_roas > 0


def test_channel_summary_and_long_spend_shape() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)

    channel_df = channel_summary(prepared)
    long_df = weekly_spend_long(prepared)

    assert len(channel_df) == 6
    assert set(channel_df.columns) == {
        "channel",
        "spend_gbp",
        "spend_share",
        "corr_with_revenue",
        "avg_weekly_spend_gbp",
    }
    assert len(long_df) == len(prepared) * 6


def test_promotion_and_readiness_outputs() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    prepared = prepare_weekly_frame(df)

    promo = promotion_summary(prepared)
    checks = mmm_readiness_checks(prepared)

    assert len(promo) == 2
    assert len(checks) == 4
    assert {check["status"] for check in checks}.issubset({"Pass", "Review"})

