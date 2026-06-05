"""Baseline econometric modeling utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import RegressionResultsWrapper
from statsmodels.stats.outliers_influence import variance_inflation_factor

from marketing_effectiveness_lab.analytics import (
    CHANNEL_LABELS,
    prepare_weekly_frame,
    spend_columns,
)

CONTROL_COLUMNS = [
    "trend",
    "trend_squared",
    "promotion_depth_pct",
    "promotion_flag",
    "holiday_flag",
    "season_spring_summer",
    "season_autumn_winter",
    "organic_search_sessions",
    "consumer_confidence_index",
    "inflation_rate_pct",
]


@dataclass(frozen=True)
class BaselineModelResult:
    model: RegressionResultsWrapper
    feature_frame: pd.DataFrame
    train_frame: pd.DataFrame
    test_frame: pd.DataFrame
    coefficient_table: pd.DataFrame
    vif_table: pd.DataFrame
    metrics: dict[str, float]


def make_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Create the feature frame used by the baseline econometric model."""

    model_df = prepare_weekly_frame(df)
    model_df["trend"] = np.arange(len(model_df), dtype=float)
    model_df["trend_squared"] = model_df["trend"] ** 2

    for column in spend_columns(model_df):
        model_df[f"log_{column}"] = np.log1p(model_df[column])

    model_df["log_organic_search_sessions"] = np.log1p(model_df["organic_search_sessions"])
    model_df["log_revenue_gbp"] = np.log(model_df["revenue_gbp"])
    return model_df


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Return baseline model feature columns available in the frame."""

    media_features = [f"log_{column}" for column in spend_columns(df)]
    controls = [
        "trend",
        "trend_squared",
        "promotion_depth_pct",
        "promotion_flag",
        "holiday_flag",
        "season_spring_summer",
        "season_autumn_winter",
        "log_organic_search_sessions",
        "consumer_confidence_index",
        "inflation_rate_pct",
    ]
    return media_features + controls


def fit_baseline_model(df: pd.DataFrame, holdout_weeks: int = 26) -> BaselineModelResult:
    """Fit a transparent OLS baseline with the latest weeks held out."""

    if len(df) <= holdout_weeks + 30:
        raise ValueError("Not enough rows to fit the baseline model with the requested holdout.")

    model_df = make_model_frame(df)
    features = feature_columns(model_df)
    train = model_df.iloc[:-holdout_weeks].copy()
    test = model_df.iloc[-holdout_weeks:].copy()

    x_train = sm.add_constant(train[features], has_constant="add")
    model = sm.OLS(train["log_revenue_gbp"], x_train).fit()

    train["predicted_revenue_gbp"] = np.exp(model.predict(x_train))
    x_test = sm.add_constant(test[features], has_constant="add")
    test["predicted_revenue_gbp"] = np.exp(model.predict(x_test))

    coefficient_table = _coefficient_table(model)
    vif_table = _vif_table(train[features])
    metrics = _model_metrics(train, test, model)

    return BaselineModelResult(
        model=model,
        feature_frame=model_df,
        train_frame=train,
        test_frame=test,
        coefficient_table=coefficient_table,
        vif_table=vif_table,
        metrics=metrics,
    )


def _coefficient_table(model: RegressionResultsWrapper) -> pd.DataFrame:
    rows = []
    for feature, coefficient in model.params.items():
        rows.append(
            {
                "feature": _feature_label(feature),
                "raw_feature": feature,
                "coefficient": coefficient,
                "p_value": model.pvalues[feature],
                "direction": "Positive" if coefficient >= 0 else "Negative",
            }
        )
    return pd.DataFrame(rows)


def _vif_table(features: pd.DataFrame) -> pd.DataFrame:
    x = sm.add_constant(features, has_constant="add")
    rows = []
    for idx, column in enumerate(x.columns):
        if column == "const":
            continue
        rows.append(
            {
                "feature": _feature_label(column),
                "raw_feature": column,
                "vif": variance_inflation_factor(x.to_numpy(), idx),
            }
        )
    return pd.DataFrame(rows).sort_values("vif", ascending=False)


def _model_metrics(
    train: pd.DataFrame,
    test: pd.DataFrame,
    model: RegressionResultsWrapper,
) -> dict[str, float]:
    train_mape = _mape(train["revenue_gbp"], train["predicted_revenue_gbp"])
    test_mape = _mape(test["revenue_gbp"], test["predicted_revenue_gbp"])
    test_rmse = float(
        np.sqrt(np.mean((test["revenue_gbp"] - test["predicted_revenue_gbp"]) ** 2))
    )
    return {
        "train_r_squared": float(model.rsquared),
        "train_adjusted_r_squared": float(model.rsquared_adj),
        "train_mape": train_mape,
        "test_mape": test_mape,
        "test_rmse_gbp": test_rmse,
        "holdout_weeks": float(len(test)),
    }


def _mape(actual: pd.Series, predicted: pd.Series) -> float:
    actual_values = actual.to_numpy(dtype=float)
    predicted_values = predicted.to_numpy(dtype=float)
    return float(np.mean(np.abs((actual_values - predicted_values) / actual_values)))


def _feature_label(feature: str) -> str:
    if feature == "const":
        return "Intercept"
    if feature == "log_organic_search_sessions":
        return "Organic search sessions"
    if feature.startswith("log_"):
        raw = feature.removeprefix("log_")
        return CHANNEL_LABELS.get(raw, raw.replace("_", " ").title())
    return feature.replace("_", " ").title()

