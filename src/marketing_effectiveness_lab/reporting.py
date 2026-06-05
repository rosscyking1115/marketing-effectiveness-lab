"""Executive summary helpers for portfolio and dashboard reporting."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from marketing_effectiveness_lab.analytics import KpiSummary
from marketing_effectiveness_lab.budget import BudgetScenarioResult
from marketing_effectiveness_lab.governance import RecommendationReadiness
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


def build_model_run_report(
    kpis: KpiSummary,
    mmm_result: MmmModelResult,
    scenario: BudgetScenarioResult,
    executive_summary: ExecutiveSummary,
    *,
    data_source_label: str,
    model_label: str,
    row_count: int,
    first_week: str,
    last_week: str,
    recommendation_readiness: RecommendationReadiness | None = None,
) -> str:
    """Create a deterministic markdown report for review and lightweight audit trails."""

    top_channels = mmm_result.contribution_table.sort_values(
        "estimated_contribution_gbp",
        ascending=False,
    ).head(3)
    scenario_summary = scenario.summary

    lines = [
        "# Marketing Effectiveness Model Run Report",
        "",
        "## Executive Summary",
        "",
        executive_summary.headline,
        "",
        "## Run Context",
        "",
        f"- Data source: {data_source_label}",
        f"- Modeling window: {first_week} to {last_week}",
        f"- Weekly rows: {row_count:,}",
        f"- Active response model: {model_label}",
        f"- Holdout weeks: {mmm_result.metrics['holdout_weeks']:,.0f}",
        "",
        "## KPI Snapshot",
        "",
        f"- Revenue: {_gbp(kpis.revenue_gbp)}",
        f"- Media spend: {_gbp(kpis.media_spend_gbp)}",
        f"- Blended ROAS: {kpis.blended_roas:,.1f}x",
        f"- Orders: {kpis.orders:,.0f}",
        f"- New customers: {kpis.new_customers:,.0f}",
        "",
        "## Model Diagnostics",
        "",
        f"- Train R-squared: {mmm_result.metrics['train_r_squared']:,.3f}",
        f"- Train MAPE: {_pct(mmm_result.metrics['train_mape'])}",
        f"- Holdout MAPE: {_pct(mmm_result.metrics['test_mape'])}",
        f"- Holdout RMSE: {_gbp(mmm_result.metrics['test_rmse_gbp'])}",
        "",
        "## Top Estimated Media Contributions",
        "",
        "| Channel | Contribution | Spend | ROI |",
        "| --- | ---: | ---: | ---: |",
    ]

    for channel in top_channels.to_dict("records"):
        lines.append(
            "| "
            f"{channel['channel']} | "
            f"{_gbp(channel['estimated_contribution_gbp'])} | "
            f"{_gbp(channel['spend_gbp'])} | "
            f"{channel['estimated_roi']:,.1f}x |"
        )

    lines.extend(
        [
            "",
            "## Budget Scenario",
            "",
            f"- Current weekly spend: {_gbp(scenario_summary['current_weekly_spend_gbp'])}",
            f"- Proposed weekly spend: {_gbp(scenario_summary['proposed_weekly_spend_gbp'])}",
            f"- Weekly spend change: {_gbp(scenario_summary['weekly_spend_change_gbp'])}",
            (
                "- Estimated weekly contribution change: "
                f"{_gbp(scenario_summary['weekly_contribution_change_gbp'])}"
            ),
            f"- Estimated weekly profit change: {_gbp(scenario_summary['weekly_profit_change_gbp'])}",
            f"- Proposed profit ROI: {scenario_summary['proposed_profit_roi']:,.1f}x",
            "",
        ]
    )

    if recommendation_readiness is not None:
        lines.extend(
            [
                "## Recommendation Readiness",
                "",
                f"- Status: {recommendation_readiness.status}",
                f"- Score: {recommendation_readiness.score:,.1f}/100",
                "",
                "| Check | Status | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for check in recommendation_readiness.checks.to_dict("records"):
            lines.append(f"| {check['check']} | {check['status']} | {check['detail']} |")
        if recommendation_readiness.required_actions:
            lines.extend(["", "Required actions before approval:"])
            lines.extend(f"- {action}" for action in recommendation_readiness.required_actions)
        lines.append("")

    lines.extend(
        [
            "## Recommendation",
            "",
            executive_summary.recommendation,
            "",
            "## Caveats",
            "",
        ]
    )

    lines.extend(f"- {caveat}" for caveat in executive_summary.caveats)
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- This report is generated deterministically from the current dashboard state.",
            "- It is suitable for analyst review, stakeholder discussion, and portfolio inspection.",
            "- It is not a production approval record until authentication, persistence, and audit logging are added.",
        ]
    )

    return "\n".join(lines) + "\n"


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
