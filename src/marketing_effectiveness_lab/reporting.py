"""Executive summary helpers for portfolio and dashboard reporting."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
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


@dataclass(frozen=True)
class BusinessImpactSummary:
    """A one-page, stakeholder-facing roll-up of the analysis and its decision impact."""

    headline: str
    generated_for: str
    commercial: dict[str, float]
    confidence: dict[str, object]
    recommendation: dict[str, object]
    customer: dict[str, object] | None
    caveats: list[str]


def build_business_impact_summary(
    kpis: KpiSummary,
    mmm_result: MmmModelResult,
    scenario: BudgetScenarioResult,
    readiness: RecommendationReadiness,
    executive_summary: ExecutiveSummary,
    *,
    data_source_label: str,
    customer_highlights: Mapping[str, object] | None = None,
) -> BusinessImpactSummary:
    """Aggregate existing analysis outputs into a single business-impact summary.

    Scenario deltas are read defensively (a missing delta means "no change"), but the
    model metrics are required: a missing metric should surface as an error rather than
    a misleading zero.
    """

    weekly_profit_change = float(scenario.summary.get("weekly_profit_change_gbp", 0.0))
    commercial = {
        "revenue_gbp": float(kpis.revenue_gbp),
        "media_spend_gbp": float(kpis.media_spend_gbp),
        "blended_roas": float(kpis.blended_roas),
        "orders": int(kpis.orders),
        "average_order_value_gbp": float(kpis.average_order_value_gbp),
    }
    confidence = {
        "holdout_mape": float(mmm_result.metrics["test_mape"]),
        "train_r_squared": float(mmm_result.metrics["train_r_squared"]),
        "readiness_status": readiness.status,
        "readiness_score": float(readiness.score),
    }
    recommendation = {
        "action": executive_summary.recommendation,
        "weekly_profit_change_gbp": weekly_profit_change,
        "annualized_profit_change_gbp": weekly_profit_change * 52.0,
        "weekly_spend_change_pct": float(scenario.summary.get("spend_change_pct", 0.0)),
    }
    return BusinessImpactSummary(
        headline=executive_summary.headline,
        generated_for=data_source_label,
        commercial=commercial,
        confidence=confidence,
        recommendation=recommendation,
        customer=dict(customer_highlights) if customer_highlights else None,
        caveats=list(executive_summary.caveats),
    )


def business_impact_markdown(summary: BusinessImpactSummary) -> str:
    """Render the business-impact summary as a dependency-free one-page brief."""

    commercial = summary.commercial
    confidence = summary.confidence
    recommendation = summary.recommendation

    lines = [
        "# Marketing Effectiveness - Business Impact Brief",
        "",
        f"_Prepared from: {summary.generated_for}_",
        "",
        f"**{summary.headline}**",
        "",
        "## Commercial snapshot",
        f"- Revenue: {_gbp(commercial['revenue_gbp'])}",
        f"- Media spend: {_gbp(commercial['media_spend_gbp'])}",
        f"- Blended ROAS: {commercial['blended_roas']:,.1f}x",
        f"- Orders: {int(commercial['orders']):,} at {_gbp(commercial['average_order_value_gbp'])} AOV",
        "",
        "## Recommended action and impact",
        f"- {recommendation['action']}",
        f"- Estimated weekly profit impact: {_gbp(recommendation['weekly_profit_change_gbp'])}",
        f"- Annualized (x52): {_gbp(recommendation['annualized_profit_change_gbp'])}",
        f"- Weekly spend change: {_pct(recommendation['weekly_spend_change_pct'])}",
        "",
        "## Measurement confidence",
        f"- MMM holdout accuracy (MAPE): {_pct(confidence['holdout_mape'])}",
        f"- Model fit (train R-squared): {float(confidence['train_r_squared']):,.2f}",
        f"- Recommendation readiness: {confidence['readiness_status']} "
        f"(score {float(confidence['readiness_score']):,.0f}/100)",
    ]

    if summary.customer:
        customer = summary.customer
        lines.extend(["", "## Customer economics"])
        if "source_label" in customer:
            lines.append(f"- Source: {customer['source_label']}")
        if "customers" in customer:
            lines.append(f"- Customers analysed: {int(customer['customers']):,}")
        if "repeat_purchase_rate" in customer:
            lines.append(f"- Repeat-purchase rate: {_pct(float(customer['repeat_purchase_rate']))}")
        if "mean_expected_future_margin_gbp" in customer:
            lines.append(
                f"- Mean 180-day expected future margin: "
                f"GBP {float(customer['mean_expected_future_margin_gbp']):,.2f} per customer"
            )
        if "high_lapse_risk_customers" in customer:
            lines.append(
                f"- High lapse-risk customers: {int(customer['high_lapse_risk_customers']):,}"
            )

    lines.extend(["", "## Caveats"])
    lines.extend(f"- {caveat}" for caveat in summary.caveats)
    lines.extend(
        [
            "",
            "_Directional decision support generated from current analysis outputs; "
            "not a production approval record._",
            "",
        ]
    )
    return "\n".join(lines)


def build_executive_summary(
    kpis: KpiSummary,
    mmm_result: MmmModelResult,
    scenario: BudgetScenarioResult,
) -> ExecutiveSummary:
    """Create deterministic business-facing summary text from current analysis outputs."""

    top_channel = _top_channel(mmm_result.contribution_table)
    # Scenario deltas: default to 0.0 ("no change") if absent, consistent with the
    # optional weekly_profit_change_gbp handling below. (Model metrics keep direct
    # access so a missing metric fails loudly rather than reporting a false zero.)
    scenario_lift = scenario.summary.get("weekly_contribution_change_gbp", 0.0)
    scenario_lift_pct = scenario.summary.get("contribution_change_pct", 0.0)
    scenario_profit_lift = scenario.summary.get("weekly_profit_change_gbp")
    spend_change_pct = scenario.summary.get("spend_change_pct", 0.0)

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


def build_model_run_manifest(
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
) -> dict[str, object]:
    """Create a deterministic machine-readable model-run manifest."""

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "run_context": {
            "data_source": data_source_label,
            "modeling_window": {
                "first_week": first_week,
                "last_week": last_week,
                "weekly_rows": row_count,
            },
            "active_model": model_label,
            "holdout_weeks": int(mmm_result.metrics["holdout_weeks"]),
        },
        "kpis": {
            "revenue_gbp": _round_float(kpis.revenue_gbp),
            "media_spend_gbp": _round_float(kpis.media_spend_gbp),
            "blended_roas": _round_float(kpis.blended_roas),
            "orders": _round_float(kpis.orders),
            "new_customers": _round_float(kpis.new_customers),
        },
        "model_diagnostics": {
            "train_r_squared": _round_float(mmm_result.metrics["train_r_squared"], digits=6),
            "train_mape": _round_float(mmm_result.metrics["train_mape"], digits=6),
            "holdout_mape": _round_float(mmm_result.metrics["test_mape"], digits=6),
            "holdout_rmse_gbp": _round_float(mmm_result.metrics["test_rmse_gbp"]),
        },
        "scenario_summary": {
            key: _json_safe_float(value)
            for key, value in sorted(scenario.summary.items())
        },
        "top_media_contributions": _manifest_contributions(mmm_result.contribution_table),
        "executive_summary": {
            "headline": executive_summary.headline,
            "recommendation": executive_summary.recommendation,
            "caveats": executive_summary.caveats,
        },
    }

    if recommendation_readiness is not None:
        payload["recommendation_readiness"] = {
            "status": recommendation_readiness.status,
            "score": recommendation_readiness.score,
            "checks": recommendation_readiness.checks.to_dict("records"),
            "required_actions": recommendation_readiness.required_actions,
        }

    payload = _json_safe(payload)
    payload["run_id"] = _manifest_run_id(payload)
    return payload


def model_run_manifest_json(manifest: dict[str, object]) -> str:
    """Serialize a model-run manifest as stable, strictly valid JSON."""

    return json.dumps(_json_safe(manifest), indent=2, sort_keys=True, allow_nan=False) + "\n"


def parse_model_run_manifest_json(manifest_json: str) -> dict[str, object]:
    """Parse and validate a model-run manifest JSON payload."""

    try:
        payload = json.loads(manifest_json)
    except json.JSONDecodeError as exc:
        msg = f"Manifest JSON is invalid: {exc.msg}."
        raise ValueError(msg) from exc

    if not isinstance(payload, dict):
        msg = "Manifest JSON must decode to an object."
        raise ValueError(msg)

    required_fields = [
        "schema_version",
        "run_id",
        "run_context",
        "model_diagnostics",
        "scenario_summary",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        msg = f"Manifest is missing required field(s): {', '.join(missing)}."
        raise ValueError(msg)

    if payload["schema_version"] != "1.0":
        msg = f"Unsupported manifest schema version: {payload['schema_version']}."
        raise ValueError(msg)

    return payload


def compare_model_run_manifests(manifests: Sequence[Mapping[str, object]]) -> pd.DataFrame:
    """Build a ranked scenario comparison table from model-run manifests."""

    if not manifests:
        msg = "At least one manifest is required for comparison."
        raise ValueError(msg)

    records = [_manifest_comparison_record(manifest, index) for index, manifest in enumerate(manifests)]
    comparison = pd.DataFrame(records)
    comparison = comparison.sort_values(
        by=["readiness_score", "weekly_profit_change_gbp", "holdout_mape"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)
    comparison.insert(0, "comparison_rank", range(1, len(comparison) + 1))
    return comparison


def model_run_manifest_comparison_csv(comparison: pd.DataFrame) -> str:
    """Serialize a manifest comparison table as CSV."""

    return comparison.to_csv(index=False)


def _top_channel(contribution_table: pd.DataFrame) -> pd.Series:
    if contribution_table.empty:
        return pd.Series({"channel": "No channel", "estimated_contribution_gbp": 0.0})
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


def _manifest_contributions(contribution_table: pd.DataFrame) -> list[dict[str, object]]:
    top_channels = contribution_table.sort_values(
        "estimated_contribution_gbp",
        ascending=False,
    ).head(6)
    return [
        {
            "channel": str(row["channel"]),
            "spend_gbp": _round_float(row["spend_gbp"]),
            "estimated_contribution_gbp": _round_float(row["estimated_contribution_gbp"]),
            "estimated_roi": _round_float(row["estimated_roi"], digits=6),
            "contribution_share": _round_float(row["contribution_share"], digits=6),
        }
        for row in top_channels.to_dict("records")
    ]


def _manifest_run_id(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _manifest_comparison_record(
    manifest: Mapping[str, object],
    index: int,
) -> dict[str, object]:
    run_context = _mapping_value(manifest, "run_context")
    modeling_window = _mapping_value(run_context, "modeling_window")
    diagnostics = _mapping_value(manifest, "model_diagnostics")
    scenario = _mapping_value(manifest, "scenario_summary")
    readiness = _mapping_value(manifest, "recommendation_readiness")
    summary = _mapping_value(manifest, "executive_summary")
    top_media = manifest.get("top_media_contributions")
    top_channel = ""
    if isinstance(top_media, list) and top_media and isinstance(top_media[0], Mapping):
        top_channel = str(top_media[0].get("channel", ""))

    first_week = str(modeling_window.get("first_week", ""))
    last_week = str(modeling_window.get("last_week", ""))
    modeling_period = f"{first_week} to {last_week}" if first_week and last_week else ""

    return {
        "run_id": str(manifest.get("run_id", f"uploaded_manifest_{index + 1}")),
        "data_source": str(run_context.get("data_source", "")),
        "active_model": str(run_context.get("active_model", "")),
        "modeling_period": modeling_period,
        "weekly_rows": _optional_float(modeling_window.get("weekly_rows")),
        "holdout_mape": _optional_float(diagnostics.get("holdout_mape")),
        "readiness_status": str(readiness.get("status", "")),
        "readiness_score": _optional_float(readiness.get("score")),
        "current_weekly_spend_gbp": _optional_float(scenario.get("current_weekly_spend_gbp")),
        "proposed_weekly_spend_gbp": _optional_float(scenario.get("proposed_weekly_spend_gbp")),
        "weekly_spend_change_gbp": _optional_float(scenario.get("weekly_spend_change_gbp")),
        "weekly_contribution_change_gbp": _optional_float(
            scenario.get("weekly_contribution_change_gbp")
        ),
        "weekly_profit_change_gbp": _optional_float(scenario.get("weekly_profit_change_gbp")),
        "proposed_profit_roi": _optional_float(scenario.get("proposed_profit_roi")),
        "top_contribution_channel": top_channel,
        "headline": str(summary.get("headline", "")),
    }


def _mapping_value(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    numeric_value = float(value)
    if pd.isna(numeric_value):
        return None
    return numeric_value


def _round_float(value: object, digits: int = 2) -> float:
    return round(float(value), digits)


def _json_safe_float(value: object) -> float | None:
    numeric_value = float(value)
    if pd.isna(numeric_value):
        return None
    return _round_float(numeric_value)


def _json_safe(value: object) -> object:
    """Recursively make a manifest payload strictly JSON-compliant.

    Non-finite floats (NaN, inf, -inf) become ``None`` and NumPy scalar types are
    normalized to native Python, so ``json.dumps`` never emits the non-standard
    ``NaN``/``Infinity`` tokens (which strict parsers reject) and never raises on
    a NumPy type. Applied to every nested field, including ones the per-field
    helpers do not sanitize (e.g. recommendation-readiness check records).
    """

    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        numeric_value = float(value)
        return numeric_value if math.isfinite(numeric_value) else None
    return value
