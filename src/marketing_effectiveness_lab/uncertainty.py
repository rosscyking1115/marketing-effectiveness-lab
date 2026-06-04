"""Uncertainty simulation helpers for MMM outputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS, spend_columns
from marketing_effectiveness_lab.mmm import MmmModelResult


@dataclass(frozen=True)
class MmmUncertaintyResult:
    contribution_intervals: pd.DataFrame
    prediction_intervals: pd.DataFrame
    draw_count: int


def simulate_mmm_uncertainty(
    mmm_result: MmmModelResult,
    draws: int = 500,
    seed: int = 42,
    interval_width: float = 0.90,
) -> MmmUncertaintyResult:
    """Simulate coefficient uncertainty for MMM contribution and prediction intervals."""

    if draws <= 0:
        raise ValueError("draws must be positive.")
    if not 0 < interval_width < 1:
        raise ValueError("interval_width must be between 0 and 1.")

    rng = np.random.default_rng(seed)
    params = mmm_result.model.params
    covariance = _positive_semidefinite_covariance(mmm_result.model.cov_params())
    coefficient_draws = rng.multivariate_normal(params.to_numpy(dtype=float), covariance, size=draws)
    draw_frame = pd.DataFrame(coefficient_draws, columns=params.index)

    lower_q = (1 - interval_width) / 2
    upper_q = 1 - lower_q

    contribution_intervals = _contribution_intervals(
        mmm_result,
        draw_frame,
        lower_q=lower_q,
        upper_q=upper_q,
    )
    prediction_intervals = _prediction_intervals(
        mmm_result,
        draw_frame,
        lower_q=lower_q,
        upper_q=upper_q,
    )

    return MmmUncertaintyResult(
        contribution_intervals=contribution_intervals,
        prediction_intervals=prediction_intervals,
        draw_count=draws,
    )


def _contribution_intervals(
    mmm_result: MmmModelResult,
    draw_frame: pd.DataFrame,
    lower_q: float,
    upper_q: float,
) -> pd.DataFrame:
    rows = []
    full_frame = mmm_result.feature_frame

    for spend_column in spend_columns(full_frame):
        feature = f"{spend_column}_mmm"
        feature_sum = float(full_frame[feature].sum())
        spend = float(full_frame[spend_column].sum())
        sampled_coefficients = draw_frame[feature].clip(lower=0)
        contribution_draws = sampled_coefficients * feature_sum

        mean_contribution = float(contribution_draws.mean())
        lower = float(contribution_draws.quantile(lower_q))
        upper = float(contribution_draws.quantile(upper_q))
        rows.append(
            {
                "channel": CHANNEL_LABELS[spend_column],
                "spend_gbp": spend,
                "contribution_mean_gbp": mean_contribution,
                "contribution_lower_gbp": lower,
                "contribution_upper_gbp": upper,
                "roi_mean": mean_contribution / spend if spend else 0.0,
                "roi_lower": lower / spend if spend else 0.0,
                "roi_upper": upper / spend if spend else 0.0,
            }
        )

    return pd.DataFrame(rows).sort_values("contribution_mean_gbp", ascending=False)


def _prediction_intervals(
    mmm_result: MmmModelResult,
    draw_frame: pd.DataFrame,
    lower_q: float,
    upper_q: float,
) -> pd.DataFrame:
    test = mmm_result.test_frame.copy()
    feature_columns = list(mmm_result.model.params.index)
    design = pd.DataFrame({"const": 1.0}, index=test.index)
    for feature in feature_columns:
        if feature == "const":
            continue
        design[feature] = test[feature]
    design = design[feature_columns]

    prediction_draws = draw_frame.to_numpy(dtype=float) @ design.to_numpy(dtype=float).T
    prediction_draws = np.clip(prediction_draws, 0, None)
    test["prediction_mean_gbp"] = prediction_draws.mean(axis=0)
    test["prediction_lower_gbp"] = np.quantile(prediction_draws, lower_q, axis=0)
    test["prediction_upper_gbp"] = np.quantile(prediction_draws, upper_q, axis=0)

    return test[
        [
            "week_start",
            "revenue_gbp",
            "predicted_revenue_gbp",
            "prediction_mean_gbp",
            "prediction_lower_gbp",
            "prediction_upper_gbp",
        ]
    ].copy()


def _positive_semidefinite_covariance(covariance: pd.DataFrame) -> np.ndarray:
    matrix = covariance.to_numpy(dtype=float)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    matrix = (matrix + matrix.T) / 2
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    eigenvalues = np.clip(eigenvalues, 1e-9, None)
    return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

