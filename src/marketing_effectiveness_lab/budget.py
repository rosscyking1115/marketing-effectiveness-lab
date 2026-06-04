"""Budget scenario planning on top of MMM foundation response curves."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS, spend_columns
from marketing_effectiveness_lab.mmm import MmmModelResult, hill_saturation


@dataclass(frozen=True)
class BudgetScenarioResult:
    summary: dict[str, float]
    channel_table: pd.DataFrame


def current_weekly_spend(df: pd.DataFrame, lookback_weeks: int = 13) -> dict[str, float]:
    """Return average weekly spend by channel over the latest lookback window."""

    if lookback_weeks <= 0:
        raise ValueError("lookback_weeks must be positive.")

    latest = df.sort_values("week_start").tail(lookback_weeks)
    return {column: float(latest[column].mean()) for column in spend_columns(latest)}


def response_for_weekly_spend(
    spend_gbp: float,
    spend_column: str,
    mmm_result: MmmModelResult,
) -> float:
    """Estimate weekly contribution for a channel at a given weekly spend level."""

    params = mmm_result.media_parameters[spend_column]
    coefficient = max(float(mmm_result.model.params.get(f"{spend_column}_mmm", 0.0)), 0.0)
    steady_state_adstock = max(spend_gbp, 0.0) / (1 - params["adstock_decay"])
    saturated = hill_saturation(
        np.array([steady_state_adstock]),
        params["half_saturation"],
        params["slope"],
    )[0]
    return float(saturated * coefficient)


def evaluate_budget_scenario(
    df: pd.DataFrame,
    mmm_result: MmmModelResult,
    proposed_weekly_spend: Mapping[str, float],
    lookback_weeks: int = 13,
) -> BudgetScenarioResult:
    """Compare current weekly spend with a proposed channel allocation."""

    current_spend = current_weekly_spend(df, lookback_weeks=lookback_weeks)
    missing_channels = set(current_spend).difference(proposed_weekly_spend)
    if missing_channels:
        raise ValueError(f"Missing proposed spend for: {', '.join(sorted(missing_channels))}")

    rows = []
    for spend_column, current_value in current_spend.items():
        proposed_value = max(float(proposed_weekly_spend[spend_column]), 0.0)
        current_contribution = response_for_weekly_spend(current_value, spend_column, mmm_result)
        proposed_contribution = response_for_weekly_spend(proposed_value, spend_column, mmm_result)
        spend_change = proposed_value - current_value
        contribution_change = proposed_contribution - current_contribution

        rows.append(
            {
                "channel": CHANNEL_LABELS[spend_column],
                "spend_column": spend_column,
                "current_weekly_spend_gbp": current_value,
                "proposed_weekly_spend_gbp": proposed_value,
                "weekly_spend_change_gbp": spend_change,
                "current_weekly_contribution_gbp": current_contribution,
                "proposed_weekly_contribution_gbp": proposed_contribution,
                "weekly_contribution_change_gbp": contribution_change,
                "proposed_roi": proposed_contribution / proposed_value if proposed_value else 0.0,
                "incremental_roi": contribution_change / spend_change if spend_change > 0 else np.nan,
            }
        )

    channel_table = pd.DataFrame(rows).sort_values("proposed_weekly_spend_gbp", ascending=False)
    current_total_spend = float(channel_table["current_weekly_spend_gbp"].sum())
    proposed_total_spend = float(channel_table["proposed_weekly_spend_gbp"].sum())
    current_total_contribution = float(channel_table["current_weekly_contribution_gbp"].sum())
    proposed_total_contribution = float(channel_table["proposed_weekly_contribution_gbp"].sum())
    spend_change = proposed_total_spend - current_total_spend
    contribution_change = proposed_total_contribution - current_total_contribution

    summary = {
        "current_weekly_spend_gbp": current_total_spend,
        "proposed_weekly_spend_gbp": proposed_total_spend,
        "weekly_spend_change_gbp": spend_change,
        "current_weekly_contribution_gbp": current_total_contribution,
        "proposed_weekly_contribution_gbp": proposed_total_contribution,
        "weekly_contribution_change_gbp": contribution_change,
        "spend_change_pct": spend_change / current_total_spend if current_total_spend else 0.0,
        "contribution_change_pct": (
            contribution_change / current_total_contribution if current_total_contribution else 0.0
        ),
        "proposed_roi": proposed_total_contribution / proposed_total_spend
        if proposed_total_spend
        else 0.0,
        "incremental_roi": contribution_change / spend_change if spend_change > 0 else np.nan,
    }
    return BudgetScenarioResult(summary=summary, channel_table=channel_table)


def allocation_from_shares(
    current_spend: Mapping[str, float],
    shares: Mapping[str, float],
    total_budget_gbp: float,
) -> dict[str, float]:
    """Convert channel shares into proposed weekly spend values."""

    normalized = _normalized_shares(current_spend, shares)
    return {column: total_budget_gbp * normalized[column] for column in current_spend}


def roi_weighted_allocation(
    current_spend: Mapping[str, float],
    mmm_result: MmmModelResult,
    total_budget_gbp: float,
    tilt_strength: float = 0.5,
) -> dict[str, float]:
    """Tilt current spend mix toward channels with stronger estimated ROI."""

    current_total = sum(current_spend.values())
    if current_total <= 0:
        raise ValueError("Current spend total must be positive.")

    weights = {}
    for spend_column, spend in current_spend.items():
        response = response_for_weekly_spend(spend, spend_column, mmm_result)
        roi = response / spend if spend else 0.0
        current_share = spend / current_total
        weights[spend_column] = current_share * max(roi, 0.01) ** tilt_strength

    weight_total = sum(weights.values())
    return {column: total_budget_gbp * (weight / weight_total) for column, weight in weights.items()}


def _normalized_shares(
    current_spend: Mapping[str, float],
    shares: Mapping[str, float],
) -> dict[str, float]:
    missing_channels = set(current_spend).difference(shares)
    if missing_channels:
        raise ValueError(f"Missing shares for: {', '.join(sorted(missing_channels))}")

    clipped = {column: max(float(shares[column]), 0.0) for column in current_spend}
    total = sum(clipped.values())
    if total <= 0:
        current_total = sum(current_spend.values())
        return {column: spend / current_total for column, spend in current_spend.items()}
    return {column: share / total for column, share in clipped.items()}
