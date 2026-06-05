"""Bayesian MMM posterior utilities built on the active MMM feature set."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS, spend_columns
from marketing_effectiveness_lab.calibration import calibration_factors
from marketing_effectiveness_lab.mmm import MmmModelResult
from marketing_effectiveness_lab.modeling import _mape


@dataclass(frozen=True)
class BayesianMmmResult:
    posterior_coefficients: pd.DataFrame
    coefficient_summary: pd.DataFrame
    contribution_intervals: pd.DataFrame
    prediction_intervals: pd.DataFrame
    prior_table: pd.DataFrame
    diagnostics: dict[str, float]


def fit_bayesian_mmm(
    mmm_result: MmmModelResult,
    lift_tests: pd.DataFrame | None = None,
    draws: int = 800,
    seed: int = 42,
    interval_width: float = 0.90,
    media_prior_sd_multiplier: float = 0.65,
    control_prior_sd_multiplier: float = 1.50,
) -> BayesianMmmResult:
    """Fit a conjugate Bayesian linear model on transformed MMM features.

    This is a lightweight posterior layer over the existing adstock and saturation design matrix.
    It is intentionally not a full Bayesian MMM sampler over carryover and saturation parameters.
    """

    if draws <= 0:
        raise ValueError("draws must be positive.")
    if not 0 < interval_width < 1:
        raise ValueError("interval_width must be between 0 and 1.")
    if media_prior_sd_multiplier <= 0 or control_prior_sd_multiplier <= 0:
        raise ValueError("prior standard deviation multipliers must be positive.")

    rng = np.random.default_rng(seed)
    feature_names = list(mmm_result.model.params.index)
    x_train = _design_matrix(mmm_result.train_frame, feature_names)
    y_train = mmm_result.train_frame["revenue_gbp"].to_numpy(dtype=float)
    residual_sigma = _residual_sigma(mmm_result)

    prior_table = build_prior_table(
        mmm_result,
        lift_tests=lift_tests,
        media_prior_sd_multiplier=media_prior_sd_multiplier,
        control_prior_sd_multiplier=control_prior_sd_multiplier,
        residual_sigma=residual_sigma,
    )
    beta0 = prior_table["prior_mean"].to_numpy(dtype=float)
    prior_std = prior_table["prior_std"].to_numpy(dtype=float)

    beta_draws, sigma2_draws = _sample_normal_inverse_gamma_posterior(
        x_train=x_train,
        y_train=y_train,
        beta0=beta0,
        prior_std=prior_std,
        draws=draws,
        rng=rng,
    )
    posterior_coefficients = pd.DataFrame(beta_draws, columns=feature_names)

    lower_q = (1 - interval_width) / 2
    upper_q = 1 - lower_q
    coefficient_summary = _coefficient_summary(
        posterior_coefficients,
        prior_table,
        lower_q=lower_q,
        upper_q=upper_q,
    )
    contribution_intervals = _contribution_intervals(
        mmm_result,
        posterior_coefficients,
        prior_table=prior_table,
        lower_q=lower_q,
        upper_q=upper_q,
    )
    prediction_intervals = _prediction_intervals(
        mmm_result,
        posterior_coefficients,
        sigma2_draws=sigma2_draws,
        rng=rng,
        lower_q=lower_q,
        upper_q=upper_q,
    )

    diagnostics = _diagnostics(
        prediction_intervals,
        sigma2_draws=sigma2_draws,
        draws=draws,
        interval_width=interval_width,
        prior_table=prior_table,
    )

    return BayesianMmmResult(
        posterior_coefficients=posterior_coefficients,
        coefficient_summary=coefficient_summary,
        contribution_intervals=contribution_intervals,
        prediction_intervals=prediction_intervals,
        prior_table=prior_table,
        diagnostics=diagnostics,
    )


def build_prior_table(
    mmm_result: MmmModelResult,
    lift_tests: pd.DataFrame | None = None,
    media_prior_sd_multiplier: float = 0.65,
    control_prior_sd_multiplier: float = 1.50,
    residual_sigma: float | None = None,
) -> pd.DataFrame:
    """Build coefficient priors, optionally nudging media means with lift-test factors."""

    if media_prior_sd_multiplier <= 0 or control_prior_sd_multiplier <= 0:
        raise ValueError("prior standard deviation multipliers must be positive.")

    sigma = residual_sigma if residual_sigma is not None else _residual_sigma(mmm_result)
    params = mmm_result.model.params
    factor_lookup = _calibration_factor_lookup(lift_tests)
    rows = []

    for feature, coefficient in params.items():
        prior_mean = float(coefficient)
        prior_source = "MMM coefficient"
        channel = ""
        is_media = feature.endswith("_mmm")

        if is_media:
            spend_column = feature.removesuffix("_mmm")
            channel = CHANNEL_LABELS.get(spend_column, spend_column)
            factor = factor_lookup.get(channel)
            prior_mean = max(prior_mean, 0.0)
            if factor is not None:
                prior_mean *= factor
                prior_source = "Experiment-informed"
            prior_std = max(abs(prior_mean) * media_prior_sd_multiplier, sigma * 0.08)
        else:
            prior_std = max(abs(prior_mean) * control_prior_sd_multiplier, sigma * 0.20)

        rows.append(
            {
                "feature": feature,
                "channel": channel,
                "prior_mean": prior_mean,
                "prior_std": prior_std,
                "prior_source": prior_source,
            }
        )

    return pd.DataFrame(rows)


def _sample_normal_inverse_gamma_posterior(
    x_train: np.ndarray,
    y_train: np.ndarray,
    beta0: np.ndarray,
    prior_std: np.ndarray,
    draws: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    prior_variance = np.square(np.clip(prior_std, 1e-6, None))
    v0_inv = np.diag(1 / prior_variance)
    xtx = x_train.T @ x_train
    v_n_inv = _symmetric_matrix(v0_inv + xtx)
    v_n = _positive_semidefinite(np.linalg.pinv(v_n_inv))
    beta_n = v_n @ (v0_inv @ beta0 + x_train.T @ y_train)

    n_obs = x_train.shape[0]
    a0 = 2.0
    y_variance = float(np.var(y_train, ddof=1)) if n_obs > 1 else 1.0
    b0 = max(y_variance, 1.0)
    a_n = a0 + n_obs / 2
    b_n = b0 + 0.5 * (
        float(y_train.T @ y_train)
        + float(beta0.T @ v0_inv @ beta0)
        - float(beta_n.T @ v_n_inv @ beta_n)
    )
    b_n = max(b_n, 1.0)

    sigma2_draws = b_n / rng.gamma(shape=a_n, scale=1.0, size=draws)
    beta_draws = np.vstack(
        [
            rng.multivariate_normal(beta_n, _positive_semidefinite(sigma2 * v_n))
            for sigma2 in sigma2_draws
        ]
    )
    return beta_draws, sigma2_draws


def _coefficient_summary(
    posterior_coefficients: pd.DataFrame,
    prior_table: pd.DataFrame,
    lower_q: float,
    upper_q: float,
) -> pd.DataFrame:
    rows = []
    prior_lookup = prior_table.set_index("feature")
    for feature in posterior_coefficients.columns:
        draws = posterior_coefficients[feature]
        prior = prior_lookup.loc[feature]
        rows.append(
            {
                "feature": feature,
                "channel": prior["channel"],
                "prior_source": prior["prior_source"],
                "prior_mean": float(prior["prior_mean"]),
                "posterior_mean": float(draws.mean()),
                "posterior_lower": float(draws.quantile(lower_q)),
                "posterior_upper": float(draws.quantile(upper_q)),
                "probability_positive": float((draws > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def _contribution_intervals(
    mmm_result: MmmModelResult,
    posterior_coefficients: pd.DataFrame,
    prior_table: pd.DataFrame,
    lower_q: float,
    upper_q: float,
) -> pd.DataFrame:
    rows = []
    full_frame = mmm_result.feature_frame
    prior_lookup = {
        row["channel"]: row["prior_source"] for _, row in prior_table.iterrows() if row["channel"]
    }

    for spend_column in spend_columns(full_frame):
        feature = f"{spend_column}_mmm"
        channel = CHANNEL_LABELS[spend_column]
        feature_sum = float(full_frame[feature].sum())
        spend = float(full_frame[spend_column].sum())
        contribution_draws = posterior_coefficients[feature].clip(lower=0) * feature_sum
        mean_contribution = float(contribution_draws.mean())
        lower = float(contribution_draws.quantile(lower_q))
        upper = float(contribution_draws.quantile(upper_q))
        rows.append(
            {
                "channel": channel,
                "spend_gbp": spend,
                "contribution_mean_gbp": mean_contribution,
                "contribution_lower_gbp": lower,
                "contribution_upper_gbp": upper,
                "roi_mean": mean_contribution / spend if spend else 0.0,
                "roi_lower": lower / spend if spend else 0.0,
                "roi_upper": upper / spend if spend else 0.0,
                "prior_source": prior_lookup.get(channel, "MMM coefficient"),
            }
        )
    return pd.DataFrame(rows).sort_values("contribution_mean_gbp", ascending=False)


def _prediction_intervals(
    mmm_result: MmmModelResult,
    posterior_coefficients: pd.DataFrame,
    sigma2_draws: np.ndarray,
    rng: np.random.Generator,
    lower_q: float,
    upper_q: float,
) -> pd.DataFrame:
    test = mmm_result.test_frame.copy()
    feature_names = list(posterior_coefficients.columns)
    x_test = _design_matrix(test, feature_names)
    mean_draws = posterior_coefficients.to_numpy(dtype=float) @ x_test.T
    noise = rng.normal(0, np.sqrt(sigma2_draws))[:, None]
    predictive_draws = np.clip(mean_draws + noise, 0, None)

    test["posterior_prediction_mean_gbp"] = predictive_draws.mean(axis=0)
    test["posterior_prediction_lower_gbp"] = np.quantile(predictive_draws, lower_q, axis=0)
    test["posterior_prediction_upper_gbp"] = np.quantile(predictive_draws, upper_q, axis=0)
    return test[
        [
            "week_start",
            "revenue_gbp",
            "predicted_revenue_gbp",
            "posterior_prediction_mean_gbp",
            "posterior_prediction_lower_gbp",
            "posterior_prediction_upper_gbp",
        ]
    ].copy()


def _diagnostics(
    prediction_intervals: pd.DataFrame,
    sigma2_draws: np.ndarray,
    draws: int,
    interval_width: float,
    prior_table: pd.DataFrame,
) -> dict[str, float]:
    actual = prediction_intervals["revenue_gbp"]
    mean_prediction = prediction_intervals["posterior_prediction_mean_gbp"]
    covered = (
        (actual >= prediction_intervals["posterior_prediction_lower_gbp"])
        & (actual <= prediction_intervals["posterior_prediction_upper_gbp"])
    )
    interval_widths = (
        prediction_intervals["posterior_prediction_upper_gbp"]
        - prediction_intervals["posterior_prediction_lower_gbp"]
    )
    return {
        "draw_count": float(draws),
        "target_interval_width": float(interval_width),
        "holdout_coverage": float(covered.mean()),
        "holdout_mape": _mape(actual, mean_prediction),
        "posterior_sigma_mean_gbp": float(np.sqrt(sigma2_draws).mean()),
        "avg_holdout_interval_width_gbp": float(interval_widths.mean()),
        "experiment_informed_priors": float(
            (prior_table["prior_source"] == "Experiment-informed").sum()
        ),
    }


def _design_matrix(frame: pd.DataFrame, feature_names: list[str]) -> np.ndarray:
    design = pd.DataFrame(index=frame.index)
    for feature in feature_names:
        design[feature] = 1.0 if feature == "const" else frame[feature].to_numpy(dtype=float)
    return design[feature_names].to_numpy(dtype=float)


def _calibration_factor_lookup(lift_tests: pd.DataFrame | None) -> dict[str, float]:
    if lift_tests is None or lift_tests.empty:
        return {}
    factors = calibration_factors(lift_tests)
    return {
        str(row["channel"]): float(row["calibration_factor"])
        for _, row in factors.iterrows()
    }


def _residual_sigma(mmm_result: MmmModelResult) -> float:
    residuals = (
        mmm_result.train_frame["revenue_gbp"] - mmm_result.train_frame["predicted_revenue_gbp"]
    ).to_numpy(dtype=float)
    return max(float(np.std(residuals, ddof=1)), 1.0)


def _symmetric_matrix(matrix: np.ndarray) -> np.ndarray:
    return (matrix + matrix.T) / 2


def _positive_semidefinite(matrix: np.ndarray) -> np.ndarray:
    symmetric = _symmetric_matrix(np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0))
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    eigenvalues = np.clip(eigenvalues, 1e-9, None)
    return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T
