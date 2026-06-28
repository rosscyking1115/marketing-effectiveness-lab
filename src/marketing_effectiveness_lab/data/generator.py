"""Demo data generation for the Marketing Effectiveness Lab."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from marketing_effectiveness_lab.data.features import (
    holiday_flag,
    promotion_flag,
    season_autumn_winter_flag,
    season_spring_summer_flag,
)
from marketing_effectiveness_lab.data.schema import schema_as_records, validate_weekly_dataset


def geometric_adstock(values: np.ndarray, decay: float) -> np.ndarray:
    """Apply a simple geometric adstock transformation."""

    transformed = np.zeros_like(values, dtype=float)
    for idx, value in enumerate(values):
        transformed[idx] = value + (decay * transformed[idx - 1] if idx else 0.0)
    return transformed


def hill_saturation(values: np.ndarray, half_saturation: float, slope: float) -> np.ndarray:
    """Bound media response with a Hill-style saturation curve."""

    values = np.clip(values, 0, None)
    numerator = values**slope
    denominator = numerator + half_saturation**slope
    return np.divide(numerator, denominator, out=np.zeros_like(values, dtype=float), where=denominator != 0)


def seasonal_boost(weeks: pd.DatetimeIndex) -> np.ndarray:
    """Create fashion retail seasonality with stronger Q4 demand."""

    week_of_year = weeks.isocalendar().week.to_numpy(dtype=float)
    annual = np.sin(2 * np.pi * (week_of_year - 8) / 52)
    q4 = np.where(weeks.month.isin([10, 11, 12]), 0.22, 0.0)
    summer = np.where(weeks.month.isin([5, 6, 7]), 0.10, 0.0)
    january_softness = np.where(weeks.month == 1, -0.08, 0.0)
    return annual * 0.08 + q4 + summer + january_softness


def generate_weekly_demo_data(seed: int = 42) -> tuple[pd.DataFrame, dict[str, object]]:
    """Generate a realistic weekly UK fashion ecommerce marketing dataset."""

    rng = np.random.default_rng(seed)
    weeks = pd.date_range("2023-01-02", "2025-12-29", freq="W-MON")
    n_weeks = len(weeks)
    week_index = np.arange(n_weeks)

    seasonality = seasonal_boost(weeks)
    black_friday = (weeks.month == 11) & (weeks.day >= 20)
    summer_sale = weeks.month.isin([6, 7])

    # Latent promotion schedule that drives discount depth, media spend, and
    # demand. The published ``promotion_flag`` column is derived from the
    # resulting discount depth (see below) so it shares the connector-assembly
    # definition rather than this internal schedule.
    promotion_schedule = (
        black_friday
        | summer_sale
        | ((weeks.month == 3) & (weeks.day >= 18))
        | ((weeks.month == 9) & (weeks.day <= 21))
    ).astype(int)
    promotion_depth_pct = np.where(
        black_friday,
        rng.normal(28, 4, n_weeks),
        np.where(summer_sale, rng.normal(18, 3, n_weeks), rng.normal(6, 3, n_weeks)),
    )
    promotion_depth_pct = np.clip(promotion_depth_pct * (0.45 + promotion_schedule), 0, 35)

    macro_trend = np.linspace(-3, 2, n_weeks)
    consumer_confidence_index = -18 + macro_trend + rng.normal(0, 2.2, n_weeks)
    inflation_rate_pct = 6.5 - np.linspace(0, 3.2, n_weeks) + rng.normal(0, 0.35, n_weeks)

    base_media_multiplier = 1 + seasonality + (promotion_schedule * 0.35)
    paid_search_spend = rng.normal(62_000, 7_500, n_weeks) * base_media_multiplier
    paid_social_spend = rng.normal(78_000, 11_000, n_weeks) * (base_media_multiplier + 0.08)
    display_spend = rng.normal(33_000, 6_000, n_weeks) * (1 + seasonality * 0.6)
    affiliates_spend = rng.normal(26_000, 4_500, n_weeks) * (1 + promotion_schedule * 0.25)
    email_spend = rng.normal(8_500, 1_700, n_weeks) * (1 + promotion_schedule * 0.6)
    influencer_spend = rng.normal(21_000, 6_500, n_weeks) * (
        1 + weeks.month.isin([3, 4, 9, 10]).astype(float) * 0.55
    )

    channel_spend = {
        "paid_search": np.clip(paid_search_spend, 25_000, None),
        "paid_social": np.clip(paid_social_spend, 30_000, None),
        "display": np.clip(display_spend, 8_000, None),
        "affiliates": np.clip(affiliates_spend, 5_000, None),
        "email": np.clip(email_spend, 2_000, None),
        "influencer": np.clip(influencer_spend, 0, None),
    }

    media_specs = {
        "paid_search": {"decay": 0.25, "half_saturation": 92_000, "effect": 520_000},
        "paid_social": {"decay": 0.45, "half_saturation": 130_000, "effect": 470_000},
        "display": {"decay": 0.55, "half_saturation": 72_000, "effect": 180_000},
        "affiliates": {"decay": 0.15, "half_saturation": 45_000, "effect": 210_000},
        "email": {"decay": 0.10, "half_saturation": 18_000, "effect": 160_000},
        "influencer": {"decay": 0.60, "half_saturation": 65_000, "effect": 190_000},
    }

    channel_revenue_contribution: dict[str, np.ndarray] = {}
    for channel, values in channel_spend.items():
        specs = media_specs[channel]
        adstocked = geometric_adstock(values, specs["decay"])
        saturated = hill_saturation(adstocked, specs["half_saturation"], slope=1.35)
        channel_revenue_contribution[channel] = saturated * specs["effect"]

    organic_search_sessions = (
        510_000
        + week_index * 800
        + seasonality * 180_000
        + promotion_schedule * 65_000
        + rng.normal(0, 24_000, n_weeks)
    )
    organic_search_sessions = np.clip(organic_search_sessions, 280_000, None)

    baseline_revenue = (
        1_850_000
        + week_index * 5_200
        + seasonality * 1_350_000
        + promotion_depth_pct * 22_000
        + (consumer_confidence_index + 20) * 18_000
        - inflation_rate_pct * 42_000
        + organic_search_sessions * 0.95
    )
    media_revenue = sum(channel_revenue_contribution.values())
    noise = rng.normal(0, 170_000, n_weeks)
    revenue = np.clip(baseline_revenue + media_revenue + noise, 500_000, None)

    average_order_value = np.clip(
        61 + seasonality * 7 - promotion_depth_pct * 0.28 + rng.normal(0, 2.4, n_weeks),
        38,
        None,
    )
    orders = np.round(revenue / average_order_value).astype(int)
    new_customer_rate = np.clip(0.28 + channel_spend["paid_social"] / 1_100_000 * 0.25, 0.22, 0.47)
    new_customers = np.round(orders * new_customer_rate + rng.normal(0, 600, n_weeks)).astype(int)

    # Publish the rounded depth and derive the flag from that same value so the
    # demo data is internally consistent with the connector-assembly rule.
    published_promotion_depth_pct = np.round(promotion_depth_pct, 2)

    df = pd.DataFrame(
        {
            "week_start": weeks.strftime("%Y-%m-%d"),
            "revenue_gbp": np.round(revenue, 2),
            "orders": orders,
            "new_customers": np.clip(new_customers, 0, None),
            "average_order_value_gbp": np.round(average_order_value, 2),
            "paid_search_spend_gbp": np.round(channel_spend["paid_search"], 2),
            "paid_social_spend_gbp": np.round(channel_spend["paid_social"], 2),
            "display_spend_gbp": np.round(channel_spend["display"], 2),
            "affiliates_spend_gbp": np.round(channel_spend["affiliates"], 2),
            "email_spend_gbp": np.round(channel_spend["email"], 2),
            "influencer_spend_gbp": np.round(channel_spend["influencer"], 2),
            "organic_search_sessions": np.round(organic_search_sessions).astype(int),
            "promotion_depth_pct": published_promotion_depth_pct,
            "promotion_flag": promotion_flag(published_promotion_depth_pct),
            "holiday_flag": holiday_flag(weeks.month),
            "season_spring_summer": season_spring_summer_flag(weeks.month),
            "season_autumn_winter": season_autumn_winter_flag(weeks.month),
            "consumer_confidence_index": np.round(consumer_confidence_index, 2),
            "inflation_rate_pct": np.round(inflation_rate_pct, 2),
        }
    )

    ground_truth = {
        "scenario": "UK fashion ecommerce weekly marketing effectiveness demo dataset",
        "seed": seed,
        "start_week": str(weeks.min().date()),
        "end_week": str(weeks.max().date()),
        "currency": "GBP",
        "grain": "weekly",
        "media_specs": media_specs,
        "notes": [
            "Revenue includes baseline demand, seasonality, promotions, macro controls, "
            "organic demand, and media effects.",
            "Media effects are generated with geometric adstock and Hill-style saturation.",
            "Ground truth is included for model validation during development and should "
            "not be used as a production assumption.",
        ],
        "schema": schema_as_records(),
    }
    return df, ground_truth


def write_outputs(df: pd.DataFrame, ground_truth: dict[str, object], output_dir: Path) -> None:
    """Write generated weekly, long-channel, and metadata outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / "fashion_retail_weekly.csv", index=False)

    channel_columns = [column for column in df.columns if column.endswith("_spend_gbp")]
    long_spend = df.melt(
        id_vars=["week_start"],
        value_vars=channel_columns,
        var_name="channel",
        value_name="spend_gbp",
    )
    long_spend["channel"] = long_spend["channel"].str.replace("_spend_gbp", "", regex=False)
    long_spend.to_csv(output_dir / "channel_spend_weekly_long.csv", index=False)

    with (output_dir / "ground_truth_metadata.json").open("w", encoding="utf-8") as fp:
        json.dump(ground_truth, fp, indent=2)


def generate_and_validate(output_dir: Path, seed: int = 42) -> pd.DataFrame:
    """Generate, validate, and write the demo dataset."""

    df, ground_truth = generate_weekly_demo_data(seed=seed)
    errors = validate_weekly_dataset(df)
    if errors:
        raise ValueError("Dataset validation failed:\n- " + "\n- ".join(errors))

    write_outputs(df, ground_truth, output_dir)
    return df
