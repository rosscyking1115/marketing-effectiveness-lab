from __future__ import annotations

import pandas as pd

from marketing_effectiveness_lab.data.features import PROMOTION_DEPTH_THRESHOLD_PCT
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.data.schema import SPEND_COLUMNS, validate_weekly_dataset


def test_generated_demo_data_matches_schema() -> None:
    df, _ = generate_weekly_demo_data(seed=42)

    assert validate_weekly_dataset(df) == []
    assert len(df) == 157
    assert pd.to_datetime(df["week_start"]).min() == pd.Timestamp("2023-01-02")
    assert pd.to_datetime(df["week_start"]).max() == pd.Timestamp("2025-12-29")


def test_generated_demo_data_has_commercial_signal() -> None:
    df, _ = generate_weekly_demo_data(seed=42)

    assert df["revenue_gbp"].min() > 0
    assert df["orders"].min() > 0
    assert df["new_customers"].min() >= 0
    assert df[list(SPEND_COLUMNS)].sum().sum() > 30_000_000
    assert df["promotion_flag"].sum() > 0
    assert df["holiday_flag"].sum() > 0


def test_demo_features_match_shared_canonical_definitions() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    month = pd.to_datetime(df["week_start"]).dt.month

    # Season flags are exact complements: every week belongs to exactly one
    # season, so neither both-zero nor both-one rows should exist.
    assert (df["season_spring_summer"] + df["season_autumn_winter"] == 1).all()
    assert month[df["season_spring_summer"] == 1].isin(range(3, 9)).all()

    # Holiday and promotion flags use the same definitions as connector assembly.
    assert (df["holiday_flag"] == month.isin([11, 12]).astype(int)).all()
    expected_promotion = (df["promotion_depth_pct"] >= PROMOTION_DEPTH_THRESHOLD_PCT).astype(int)
    assert (df["promotion_flag"] == expected_promotion).all()


def test_schema_rejects_negative_spend() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    df.loc[0, "paid_search_spend_gbp"] = -1

    errors = validate_weekly_dataset(df)

    assert "paid_search_spend_gbp contains negative values." in errors
