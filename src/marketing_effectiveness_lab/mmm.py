"""MMM foundation utilities: adstock, saturation, and contribution estimates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import RegressionResultsWrapper

from marketing_effectiveness_lab.analytics import (
    CHANNEL_LABELS,
    prepare_weekly_frame,
    spend_columns,
)
from marketing_effectiveness_lab.modeling import _mape

DEFAULT_MEDIA_PARAMETERS = {
    "paid_search_spend_gbp": {"adstock_decay": 0.25, "half_saturation": 92_000.0, "slope": 1.35},
    "paid_social_spend_gbp": {"adstock_decay": 0.45, "half_saturation": 130_000.0, "slope": 1.35},
    "display_spend_gbp": {"adstock_decay": 0.55, "half_saturation": 72_000.0, "slope": 1.35},
    "affiliates_spend_gbp": {"adstock_decay": 0.15, "half_saturation": 45_000.0, "slope": 1.35},
    "email_spend_gbp": {"adstock_decay": 0.10, "half_saturation": 18_000.0, "slope": 1.35},
    "influencer_spend_gbp": {"adstock_decay": 0.60, "half_saturation": 65_000.0, "slope": 1.35},
}

# season_spring_summer and season_autumn_winter are exact complements, so only
# one is used as a control alongside the intercept (autumn/winter is the
# reference season). Including both would make the design matrix rank-deficient.
CONTROL_FEATURES = [
    "trend",
    "trend_squared",
    "promotion_depth_pct",
    "promotion_flag",
    "holiday_flag",
    "season_spring_summer",
    "log_organic_search_sessions",
    "consumer_confidence_index",
    "inflation_rate_pct",
]


@dataclass(frozen=True)
class MmmModelResult:
    model: RegressionResultsWrapper
    media_parameters: dict[str, dict[str, float]]
    feature_frame: pd.DataFrame
    train_frame: pd.DataFrame
    test_frame: pd.DataFrame
    contribution_table: pd.DataFrame
    response_curves: pd.DataFrame
    parameter_table: pd.DataFrame
    metrics: dict[str, float]


@dataclass(frozen=True)
class MmmCalibrationResult:
    mmm_result: MmmModelResult
    search_table: pd.DataFrame
    best_parameters: dict[str, dict[str, float]]


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


def make_mmm_frame(
    df: pd.DataFrame,
    media_parameters: Mapping[str, Mapping[str, float]] | None = None,
) -> pd.DataFrame:
    """Create MMM-style transformed media features and controls."""

    parameters = _resolved_media_parameters(media_parameters)
    mmm_df = prepare_weekly_frame(df)
    mmm_df["trend"] = np.arange(len(mmm_df), dtype=float)
    mmm_df["trend_squared"] = mmm_df["trend"] ** 2
    mmm_df["log_organic_search_sessions"] = np.log1p(mmm_df["organic_search_sessions"])

    for column in spend_columns(mmm_df):
        params = parameters[column]
        adstocked = geometric_adstock(mmm_df[column], params["adstock_decay"])
        saturated = hill_saturation(adstocked, params["half_saturation"], params["slope"])
        mmm_df[f"{column}_adstocked"] = adstocked
        mmm_df[f"{column}_mmm"] = saturated

    return mmm_df


def mmm_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return transformed media plus control feature columns."""

    media_features = [f"{column}_mmm" for column in spend_columns(df)]
    return media_features + CONTROL_FEATURES


def fit_mmm_foundation_model(
    df: pd.DataFrame,
    holdout_weeks: int = 26,
    media_parameters: Mapping[str, Mapping[str, float]] | None = None,
) -> MmmModelResult:
    """Fit a deterministic MMM-style model with transformed media variables."""

    if len(df) <= holdout_weeks + 30:
        raise ValueError("Not enough rows to fit the MMM foundation model with the requested holdout.")

    parameters = _resolved_media_parameters(media_parameters)
    feature_frame = make_mmm_frame(df, media_parameters=parameters)
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
        media_parameters=parameters,
        feature_frame=feature_frame,
        train_frame=train,
        test_frame=test,
        contribution_table=_contribution_table(feature_frame, model),
        response_curves=_response_curves(feature_frame, model, parameters),
        parameter_table=_parameter_table(parameters),
        metrics=_metrics(train, test, model),
    )


def calibrate_mmm_parameters(
    df: pd.DataFrame,
    holdout_weeks: int = 26,
    validation_weeks: int = 20,
    decay_candidates: tuple[float, ...] = (0.10, 0.30, 0.50, 0.70),
    half_saturation_multipliers: tuple[float, ...] = (0.70, 1.00, 1.30),
) -> MmmCalibrationResult:
    """Tune adstock and saturation parameters with a small time-aware validation search."""

    if len(df) <= holdout_weeks + validation_weeks + 30:
        raise ValueError("Not enough rows to calibrate MMM parameters with the requested splits.")

    best_parameters = _resolved_media_parameters()
    calibration_df = prepare_weekly_frame(df).iloc[:-holdout_weeks].copy()
    search_rows = []

    for channel in spend_columns(calibration_df):
        channel_best = best_parameters[channel].copy()
        channel_best_mape = float("inf")
        default_half_saturation = DEFAULT_MEDIA_PARAMETERS[channel]["half_saturation"]

        for decay in decay_candidates:
            for multiplier in half_saturation_multipliers:
                candidate_parameters = _copy_parameters(best_parameters)
                candidate_parameters[channel] = {
                    "adstock_decay": decay,
                    "half_saturation": default_half_saturation * multiplier,
                    "slope": DEFAULT_MEDIA_PARAMETERS[channel]["slope"],
                }
                validation_mape = _validation_mape(
                    calibration_df,
                    candidate_parameters,
                    validation_weeks=validation_weeks,
                )
                search_rows.append(
                    {
                        "channel": CHANNEL_LABELS[channel],
                        "spend_column": channel,
                        "adstock_decay": decay,
                        "half_saturation_gbp": default_half_saturation * multiplier,
                        "validation_mape": validation_mape,
                    }
                )
                if validation_mape < channel_best_mape:
                    channel_best_mape = validation_mape
                    channel_best = candidate_parameters[channel]

        best_parameters[channel] = channel_best

    mmm_result = fit_mmm_foundation_model(
        df,
        holdout_weeks=holdout_weeks,
        media_parameters=best_parameters,
    )
    return MmmCalibrationResult(
        mmm_result=mmm_result,
        search_table=pd.DataFrame(search_rows),
        best_parameters=best_parameters,
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


def _response_curves(
    df: pd.DataFrame,
    model: RegressionResultsWrapper,
    media_parameters: Mapping[str, Mapping[str, float]],
) -> pd.DataFrame:
    rows = []
    for spend_column in spend_columns(df):
        params = media_parameters[spend_column]
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


def _parameter_table(media_parameters: Mapping[str, Mapping[str, float]]) -> pd.DataFrame:
    rows = []
    for column, params in media_parameters.items():
        rows.append(
            {
                "channel": CHANNEL_LABELS[column],
                "adstock_decay": params["adstock_decay"],
                "half_saturation_gbp": params["half_saturation"],
                "slope": params["slope"],
            }
        )
    return pd.DataFrame(rows)


def _validation_mape(
    calibration_df: pd.DataFrame,
    media_parameters: Mapping[str, Mapping[str, float]],
    validation_weeks: int,
) -> float:
    feature_frame = make_mmm_frame(calibration_df, media_parameters=media_parameters)
    features = mmm_feature_columns(feature_frame)
    train = feature_frame.iloc[:-validation_weeks].copy()
    validation = feature_frame.iloc[-validation_weeks:].copy()

    x_train = sm.add_constant(train[features], has_constant="add")
    model = sm.OLS(train["revenue_gbp"], x_train).fit()
    x_validation = sm.add_constant(validation[features], has_constant="add")
    validation_prediction = model.predict(x_validation).clip(lower=0)
    return _mape(validation["revenue_gbp"], validation_prediction)


def _resolved_media_parameters(
    media_parameters: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, dict[str, float]]:
    resolved = _copy_parameters(DEFAULT_MEDIA_PARAMETERS)
    if media_parameters:
        for channel, params in media_parameters.items():
            resolved[channel] = {
                "adstock_decay": float(params["adstock_decay"]),
                "half_saturation": float(params["half_saturation"]),
                "slope": float(params["slope"]),
            }
    return resolved


def _copy_parameters(
    media_parameters: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, float]]:
    return {
        channel: {
            "adstock_decay": float(params["adstock_decay"]),
            "half_saturation": float(params["half_saturation"]),
            "slope": float(params["slope"]),
        }
        for channel, params in media_parameters.items()
    }


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
