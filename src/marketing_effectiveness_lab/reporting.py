"""Executive summary helpers for portfolio and dashboard reporting."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from marketing_effectiveness_lab.analytics import KpiSummary
from marketing_effectiveness_lab.budget import BudgetScenarioResult
from marketing_effectiveness_lab.mmm import MmmModelResult


@dataclass(frozen=True)
class ExecutiveSummary:
    headline: str
    highlights: list[str]
    recommendation: str
    caveats: list[str]


def build_executive_summary(
    kpis: KpiSummary,
    mmm_result: MmmModelResult,
    scenario: BudgetScenarioResult,
) -> ExecutiveSummary:
    """Create deterministic business-facing summary text from current analysis outputs."""

    top_channel = _top_channel(mmm_result.contribution_table)
    scenario_lift = scenario.summary["weekly_contribution_change_gbp"]
    scenario_lift_pct = scenario.summary["contribution_change_pct"]
    scenario_profit_lift = scenario.summary.get("weekly_profit_change_gbp")
    spend_change_pct = scenario.summary["spend_change_pct"]

    if scenario_profit_lift is not None and scenario_profit_lift > 0:
        headline = (
            "The proposed allocation is directionally profitable, with estimated weekly "
            f"contribution profit up {_gbp(scenario_profit_lift)}."
        )
    elif scenario_profit_lift is not None and scenario_profit_lift < 0:
        headline = (
            "The proposed allocation is directionally weaker, with estimated weekly "
            f"contribution profit down {_gbp(abs(scenario_profit_lift))}."
        )
    elif scenario_lift > 0:
        headline = (
            "The proposed allocation is directionally positive, with estimated weekly "
            f"media contribution up {_pct(scenario_lift_pct)}."
        )
    elif scenario_lift < 0:
        headline = (
            "The proposed allocation is directionally weaker, with estimated weekly "
            f"media contribution down {_pct(abs(scenario_lift_pct))}."
        )
    else:
        headline = "The proposed allocation is broadly neutral versus the current spend mix."

    highlights = [
        f"Total selected revenue is {_gbp(kpis.revenue_gbp)} with blended ROAS of {kpis.blended_roas:,.1f}x.",
        (
            f"{top_channel['channel']} has the largest estimated media contribution at "
            f"{_gbp(top_channel['estimated_contribution_gbp'])}."
        ),
        (
            f"The scenario changes weekly spend by {_pct(spend_change_pct)} and estimated "
            f"weekly contribution by {_gbp(scenario_lift)}."
        ),
        f"Estimated weekly contribution profit changes by {_gbp(scenario_profit_lift)}."
        if scenario_profit_lift is not None
        else "Profit-aware planning is not enabled for this scenario.",
        (
            f"MMM foundation holdout MAPE is {_pct(mmm_result.metrics['test_mape'])}, "
            "useful for directional planning but not final budget approval."
        ),
    ]

    if scenario_profit_lift is not None and scenario_profit_lift > 0:
        recommendation = (
            "Use this scenario as a candidate reallocation for deeper review. Prioritize checking "
            "channel constraints, campaign availability, and whether profitable channels can absorb spend."
        )
    elif scenario_profit_lift is not None and scenario_profit_lift < 0:
        recommendation = (
            "Do not advance this scenario without revision. Review channels with lower estimated ROI "
            "or weaker profit impact before considering budget movement."
        )
    elif scenario_lift > 0:
        recommendation = (
            "Use this scenario as a candidate reallocation for deeper review. Prioritize checking "
            "channel constraints, campaign availability, and whether high-ROI channels can absorb spend."
        )
    elif scenario_lift < 0:
        recommendation = (
            "Do not advance this scenario without revision. Review channels with lower estimated ROI "
            "and test a smaller reallocation before considering budget movement."
        )
    else:
        recommendation = (
            "Treat this as a neutral planning baseline. Use manual shares or ROI-weighted tilt to "
            "explore more meaningful reallocations."
        )

    caveats = [
        "Scenario outputs use deterministic MMM foundation response curves, not Bayesian uncertainty.",
        "Contribution estimates are directional and should be calibrated with experiments where possible.",
        (
            "Profit metrics use a gross margin assumption and do not yet include inventory, "
            "channel capacity, or brand constraints."
        ),
    ]

    return ExecutiveSummary(
        headline=headline,
        highlights=highlights,
        recommendation=recommendation,
        caveats=caveats,
    )


def _top_channel(contribution_table: pd.DataFrame) -> pd.Series:
    return contribution_table.sort_values("estimated_contribution_gbp", ascending=False).iloc[0]


def _gbp(value: float) -> str:
    prefix = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{prefix}GBP {absolute / 1_000_000:,.1f}M"
    if absolute >= 1_000:
        return f"{prefix}GBP {absolute / 1_000:,.0f}K"
    return f"{prefix}GBP {absolute:,.0f}"


def _pct(value: float) -> str:
    return f"{value * 100:,.1f}%"
