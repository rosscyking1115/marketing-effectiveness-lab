"""MMM foundation utilities: adstock, saturation, and contribution estimates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import RegressionResultsWrapper

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS, prepare_weekly_frame, spend_columns
from marketing_effectiveness_lab.modeling import _mape


DEFAULT_MEDIA_PARAMETERS = {
    "paid_search_spend_gbp": {"adstock_decay": 0.25, "half_saturation": 92_000.0, "slope": 1.35},
    "paid_social_spend_gbp": {"adstock_decay": 0.45, "half_saturation": 130_000.0, "slope": 1.35},
    "display_spend_gbp": {"adstock_decay": 0.55, "half_saturation": 72_000.0, "slope": 1.35},
    "affiliates_spend_gbp": {"adstock_decay": 0.15, "half_saturation": 45_000.0, "slope": 1.35},
    "email_spend_gbp": {"adstock_decay": 0.10, "half_saturation": 18_000.0, "slope": 1.35},
    "influencer_spend_gbp": {"adstock_decay": 0.60, "half_saturation": 65_000.0, "slope": 1.35},
}

CONTROL_FEATURES = [
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


@dataclass(frozen=True)
class MmmModelResult:
    model: RegressionResultsWrapper
    feature_frame: pd.DataFrame
    train_frame: pd.DataFrame
    test_frame: pd.DataFrame
    contribution_table: pd.DataFrame
    response_curves: pd.DataFrame
    parameter_table: pd.DataFrame
    metrics: dict[str, float]


def geometric_adstock(values: pd.Series | np.ndarray, decay: float) -> np.ndarray:
    """Apply geometric adstock to a spend series."""

    raw_values = np.asarray(values, dtype=float)
    transformed = np.zeros_like(raw_values, dtype=float)
    for idx, value in enumerate(raw_values):
        transformed[idx] = value + (decay * transformed[idx - 1] if idx else 0.0)
    return transformed


def hill_saturation(values: pd.Series | np.ndarray, half_saturation: float, slope: float) -> np.ndarray:
    """Apply a Hill-style diminishing returns curve."""

    raw_values = np.clip(np.asarray(values, dtype=float), 0, None)
    numerator = raw_values**slope
    denominator = numerator + half_saturation**slope
    return np.divide(numerator, denominator, out=np.zeros_like(raw_values), where=denominator != 0)


def make_mmm_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Create MMM-style transformed media features and controls."""

    mmm_df = prepare_weekly_frame(df)
    mmm_df["trend"] = np.arange(len(mmm_df), dtype=float)
    mmm_df["trend_squared"] = mmm_df["trend"] ** 2
    mmm_df["log_organic_search_sessions"] = np.log1p(mmm_df["organic_search_sessions"])

    for column in spend_columns(mmm_df):
        params = DEFAULT_MEDIA_PARAMETERS[column]
        adstocked = geometric_adstock(mmm_df[column], params["adstock_decay"])
        saturated = hill_saturation(adstocked, params["half_saturation"], params["slope"])
        mmm_df[f"{column}_adstocked"] = adstocked
        mmm_df[f"{column}_mmm"] = saturated

    return mmm_df


def mmm_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return transformed media plus control feature columns."""

    media_features = [f"{column}_mmm" for column in spend_columns(df)]
    return media_features + CONTROL_FEATURES


def fit_mmm_foundation_model(df: pd.DataFrame, holdout_weeks: int = 26) -> MmmModelResult:
    """Fit a deterministic MMM-style model with transformed media variables."""

    if len(df) <= holdout_weeks + 30:
        raise ValueError("Not enough rows to fit the MMM foundation model with the requested holdout.")

    feature_frame = make_mmm_frame(df)
    features = mmm_feature_columns(feature_frame)
    train = feature_frame.iloc[:-holdout_weeks].copy()
    test = feature_frame.iloc[-holdout_weeks:].copy()

    x_train = sm.add_constant(train[features], has_constant="add")
    model = sm.OLS(train["revenue_gbp"], x_train).fit()

    train["predicted_revenue_gbp"] = model.predict(x_train).clip(lower=0)
    x_test = sm.add_constant(test[features], has_constant="add")
    test["predicted_revenue_gbp"] = model.predict(x_test).clip(lower=0)

    return MmmModelResult(
        model=model,
        feature_frame=feature_frame,
        train_frame=train,
        test_frame=test,
        contribution_table=_contribution_table(feature_frame, model),
        response_curves=_response_curves(feature_frame, model),
        parameter_table=_parameter_table(),
        metrics=_metrics(train, test, model),
    )


def _contribution_table(df: pd.DataFrame, model: RegressionResultsWrapper) -> pd.DataFrame:
    rows = []
    for spend_column in spend_columns(df):
        feature = f"{spend_column}_mmm"
        coefficient = max(float(model.params.get(feature, 0.0)), 0.0)
        contribution = df[feature].to_numpy(dtype=float) * coefficient
        spend = float(df[spend_column].sum())
        total_contribution = float(contribution.sum())
        rows.append(
            {
                "channel": CHANNEL_LABELS[spend_column],
                "spend_gbp": spend,
                "estimated_contribution_gbp": total_contribution,
                "estimated_roi": total_contribution / spend if spend else 0.0,
                "avg_weekly_contribution_gbp": float(contribution.mean()),
                "coefficient": coefficient,
            }
        )

    table = pd.DataFrame(rows)
    contribution_total = table["estimated_contribution_gbp"].sum()
    table["contribution_share"] = (
        table["estimated_contribution_gbp"] / contribution_total if contribution_total else 0.0
    )
    return table.sort_values("estimated_contribution_gbp", ascending=False)


def _response_curves(df: pd.DataFrame, model: RegressionResultsWrapper) -> pd.DataFrame:
    rows = []
    for spend_column in spend_columns(df):
        params = DEFAULT_MEDIA_PARAMETERS[spend_column]
        coefficient = max(float(model.params.get(f"{spend_column}_mmm", 0.0)), 0.0)
        max_spend = max(float(df[spend_column].quantile(0.98)) * 1.5, 1.0)
        spend_grid = np.linspace(0, max_spend, 60)
        saturated = hill_saturation(spend_grid, params["half_saturation"], params["slope"])
        response = saturated * coefficient
        for spend, contribution in zip(spend_grid, response, strict=True):
            rows.append(
                {
                    "channel": CHANNEL_LABELS[spend_column],
                    "spend_gbp": spend,
                    "estimated_weekly_contribution_gbp": contribution,
                }
            )
    return pd.DataFrame(rows)


def _parameter_table() -> pd.DataFrame:
    rows = []
    for column, params in DEFAULT_MEDIA_PARAMETERS.items():
        rows.append(
            {
                "channel": CHANNEL_LABELS[column],
                "adstock_decay": params["adstock_decay"],
                "half_saturation_gbp": params["half_saturation"],
                "slope": params["slope"],
            }
        )
    return pd.DataFrame(rows)


def _metrics(
    train: pd.DataFrame,
    test: pd.DataFrame,
    model: RegressionResultsWrapper,
) -> dict[str, float]:
    test_rmse = float(
        np.sqrt(np.mean((test["revenue_gbp"] - test["predicted_revenue_gbp"]) ** 2))
    )
    return {
        "train_r_squared": float(model.rsquared),
        "train_adjusted_r_squared": float(model.rsquared_adj),
        "train_mape": _mape(train["revenue_gbp"], train["predicted_revenue_gbp"]),
        "test_mape": _mape(test["revenue_gbp"], test["predicted_revenue_gbp"]),
        "test_rmse_gbp": test_rmse,
        "holdout_weeks": float(len(test)),
    }

