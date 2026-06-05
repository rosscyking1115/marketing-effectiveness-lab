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


@dataclass(frozen=True)
class BudgetOptimizationResult:
    allocation: dict[str, float]
    diagnostics: pd.DataFrame
    summary: dict[str, float]


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
    gross_margin_rate: float = 0.52,
) -> BudgetScenarioResult:
    """Compare current weekly spend with a proposed channel allocation."""

    if not 0 <= gross_margin_rate <= 1:
        raise ValueError("gross_margin_rate must be between 0 and 1.")

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
        current_gross_profit = current_contribution * gross_margin_rate
        proposed_gross_profit = proposed_contribution * gross_margin_rate
        current_profit_after_media = current_gross_profit - current_value
        proposed_profit_after_media = proposed_gross_profit - proposed_value
        profit_change = proposed_profit_after_media - current_profit_after_media

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
                "current_weekly_gross_profit_gbp": current_gross_profit,
                "proposed_weekly_gross_profit_gbp": proposed_gross_profit,
                "current_weekly_profit_after_media_gbp": current_profit_after_media,
                "proposed_weekly_profit_after_media_gbp": proposed_profit_after_media,
                "weekly_profit_change_gbp": profit_change,
                "proposed_roi": proposed_contribution / proposed_value if proposed_value else 0.0,
                "incremental_roi": contribution_change / spend_change if spend_change > 0 else np.nan,
                "proposed_profit_roi": (
                    proposed_profit_after_media / proposed_value if proposed_value else 0.0
                ),
                "incremental_profit_roi": profit_change / spend_change if spend_change > 0 else np.nan,
            }
        )

    channel_table = pd.DataFrame(rows).sort_values("proposed_weekly_spend_gbp", ascending=False)
    current_total_spend = float(channel_table["current_weekly_spend_gbp"].sum())
    proposed_total_spend = float(channel_table["proposed_weekly_spend_gbp"].sum())
    current_total_contribution = float(channel_table["current_weekly_contribution_gbp"].sum())
    proposed_total_contribution = float(channel_table["proposed_weekly_contribution_gbp"].sum())
    current_total_gross_profit = float(channel_table["current_weekly_gross_profit_gbp"].sum())
    proposed_total_gross_profit = float(channel_table["proposed_weekly_gross_profit_gbp"].sum())
    current_total_profit_after_media = float(
        channel_table["current_weekly_profit_after_media_gbp"].sum()
    )
    proposed_total_profit_after_media = float(
        channel_table["proposed_weekly_profit_after_media_gbp"].sum()
    )
    spend_change = proposed_total_spend - current_total_spend
    contribution_change = proposed_total_contribution - current_total_contribution
    profit_change = proposed_total_profit_after_media - current_total_profit_after_media

    summary = {
        "current_weekly_spend_gbp": current_total_spend,
        "proposed_weekly_spend_gbp": proposed_total_spend,
        "weekly_spend_change_gbp": spend_change,
        "current_weekly_contribution_gbp": current_total_contribution,
        "proposed_weekly_contribution_gbp": proposed_total_contribution,
        "weekly_contribution_change_gbp": contribution_change,
        "gross_margin_rate": gross_margin_rate,
        "current_weekly_gross_profit_gbp": current_total_gross_profit,
        "proposed_weekly_gross_profit_gbp": proposed_total_gross_profit,
        "current_weekly_profit_after_media_gbp": current_total_profit_after_media,
        "proposed_weekly_profit_after_media_gbp": proposed_total_profit_after_media,
        "weekly_profit_change_gbp": profit_change,
        "spend_change_pct": spend_change / current_total_spend if current_total_spend else 0.0,
        "contribution_change_pct": (
            contribution_change / current_total_contribution if current_total_contribution else 0.0
        ),
        "profit_change_pct": (
            profit_change / abs(current_total_profit_after_media)
            if current_total_profit_after_media
            else 0.0
        ),
        "proposed_roi": proposed_total_contribution / proposed_total_spend
        if proposed_total_spend
        else 0.0,
        "incremental_roi": contribution_change / spend_change if spend_change > 0 else np.nan,
        "proposed_profit_roi": (
            proposed_total_profit_after_media / proposed_total_spend
            if proposed_total_spend
            else 0.0
        ),
        "incremental_profit_roi": profit_change / spend_change if spend_change > 0 else np.nan,
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


def optimize_budget_allocation(
    current_spend: Mapping[str, float],
    mmm_result: MmmModelResult,
    total_budget_gbp: float,
    objective: str = "profit",
    gross_margin_rate: float = 0.52,
    min_share: float = 0.02,
    max_share: float = 0.45,
    steps: int = 240,
) -> BudgetOptimizationResult:
    """Recommend a constrained weekly allocation using marginal response curves."""

    if total_budget_gbp <= 0:
        raise ValueError("total_budget_gbp must be positive.")
    if objective not in {"profit", "contribution"}:
        raise ValueError("objective must be either 'profit' or 'contribution'.")
    if not 0 <= gross_margin_rate <= 1:
        raise ValueError("gross_margin_rate must be between 0 and 1.")
    if min_share < 0 or max_share <= 0 or min_share > max_share:
        raise ValueError("min_share and max_share must be non-negative and ordered.")
    if steps <= 0:
        raise ValueError("steps must be positive.")

    channels = list(current_spend)
    min_spend = {column: total_budget_gbp * min_share for column in channels}
    max_spend = {column: total_budget_gbp * max_share for column in channels}
    min_total = sum(min_spend.values())
    max_total = sum(max_spend.values())
    if min_total > total_budget_gbp + 1e-6:
        raise ValueError("Minimum share constraints exceed the total budget.")
    if max_total < total_budget_gbp - 1e-6:
        raise ValueError("Maximum share constraints cannot absorb the total budget.")

    allocation = min_spend.copy()
    remaining_budget = total_budget_gbp - min_total
    increment = total_budget_gbp / steps

    while remaining_budget > 1e-6:
        increment_value = min(increment, remaining_budget)
        best_column: str | None = None
        best_gain = -float("inf")

        for column in channels:
            if allocation[column] + increment_value > max_spend[column] + 1e-6:
                continue
            gain = _objective_value(
                allocation[column] + increment_value,
                column,
                mmm_result,
                objective=objective,
                gross_margin_rate=gross_margin_rate,
            ) - _objective_value(
                allocation[column],
                column,
                mmm_result,
                objective=objective,
                gross_margin_rate=gross_margin_rate,
            )
            if gain > best_gain:
                best_gain = gain
                best_column = column

        if best_column is None:
            best_column = min(channels, key=lambda column: allocation[column])
            increment_value = min(increment_value, max_spend[best_column] - allocation[best_column])
            if increment_value <= 1e-6:
                break

        allocation[best_column] += increment_value
        remaining_budget -= increment_value

    allocation = _rebalance_rounding_residual(allocation, max_spend, total_budget_gbp)
    diagnostics = _optimization_diagnostics(
        current_spend,
        allocation,
        mmm_result,
        objective=objective,
        gross_margin_rate=gross_margin_rate,
        min_spend=min_spend,
        max_spend=max_spend,
    )
    summary = {
        "total_budget_gbp": total_budget_gbp,
        "objective": objective,
        "gross_margin_rate": gross_margin_rate,
        "min_share": min_share,
        "max_share": max_share,
        "steps": float(steps),
        "optimized_objective_value_gbp": float(diagnostics["optimized_objective_gbp"].sum()),
        "current_mix_objective_value_gbp": float(diagnostics["current_mix_objective_gbp"].sum()),
        "objective_lift_gbp": float(diagnostics["objective_lift_gbp"].sum()),
        "channels_at_min": float((diagnostics["constraint_status"] == "At minimum").sum()),
        "channels_at_max": float((diagnostics["constraint_status"] == "At maximum").sum()),
    }
    return BudgetOptimizationResult(
        allocation=allocation,
        diagnostics=diagnostics,
        summary=summary,
    )


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


def _objective_value(
    spend_gbp: float,
    spend_column: str,
    mmm_result: MmmModelResult,
    objective: str,
    gross_margin_rate: float,
) -> float:
    contribution = response_for_weekly_spend(spend_gbp, spend_column, mmm_result)
    if objective == "contribution":
        return contribution
    return contribution * gross_margin_rate - spend_gbp


def _rebalance_rounding_residual(
    allocation: dict[str, float],
    max_spend: Mapping[str, float],
    total_budget_gbp: float,
) -> dict[str, float]:
    residual = total_budget_gbp - sum(allocation.values())
    if abs(residual) <= 1e-6:
        return allocation

    adjusted = allocation.copy()
    if residual > 0:
        for column in sorted(adjusted, key=lambda key: max_spend[key] - adjusted[key], reverse=True):
            capacity = max_spend[column] - adjusted[column]
            addition = min(residual, capacity)
            adjusted[column] += addition
            residual -= addition
            if residual <= 1e-6:
                break
    else:
        largest_column = max(adjusted, key=adjusted.get)
        adjusted[largest_column] += residual
    return adjusted


def _optimization_diagnostics(
    current_spend: Mapping[str, float],
    allocation: Mapping[str, float],
    mmm_result: MmmModelResult,
    objective: str,
    gross_margin_rate: float,
    min_spend: Mapping[str, float],
    max_spend: Mapping[str, float],
) -> pd.DataFrame:
    current_total = sum(current_spend.values())
    optimized_total = sum(allocation.values())
    rows = []
    for column, optimized_spend in allocation.items():
        current_mix_spend = optimized_total * (
            current_spend[column] / current_total if current_total else 1 / len(allocation)
        )
        optimized_objective = _objective_value(
            optimized_spend,
            column,
            mmm_result,
            objective=objective,
            gross_margin_rate=gross_margin_rate,
        )
        current_mix_objective = _objective_value(
            current_mix_spend,
            column,
            mmm_result,
            objective=objective,
            gross_margin_rate=gross_margin_rate,
        )
        if optimized_spend <= min_spend[column] + 1e-6:
            constraint_status = "At minimum"
        elif optimized_spend >= max_spend[column] - 1e-6:
            constraint_status = "At maximum"
        else:
            constraint_status = "Flexible"

        rows.append(
            {
                "channel": CHANNEL_LABELS[column],
                "spend_column": column,
                "current_mix_weekly_spend_gbp": current_mix_spend,
                "optimized_weekly_spend_gbp": optimized_spend,
                "optimized_share": optimized_spend / optimized_total if optimized_total else 0.0,
                "min_weekly_spend_gbp": min_spend[column],
                "max_weekly_spend_gbp": max_spend[column],
                "current_mix_objective_gbp": current_mix_objective,
                "optimized_objective_gbp": optimized_objective,
                "objective_lift_gbp": optimized_objective - current_mix_objective,
                "constraint_status": constraint_status,
            }
        )
    return pd.DataFrame(rows).sort_values("optimized_weekly_spend_gbp", ascending=False)
