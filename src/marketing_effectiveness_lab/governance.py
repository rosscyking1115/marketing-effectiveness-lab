"""Recommendation review gates for budget scenario governance."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from marketing_effectiveness_lab.budget import BudgetScenarioResult
from marketing_effectiveness_lab.mmm import MmmModelResult


@dataclass(frozen=True)
class RecommendationReadiness:
    status: str
    score: float
    checks: pd.DataFrame
    required_actions: list[str]


def assess_recommendation_readiness(
    mmm_result: MmmModelResult,
    scenario: BudgetScenarioResult,
    *,
    weekly_rows: int,
    evidence_quality: pd.DataFrame | None = None,
) -> RecommendationReadiness:
    """Assess whether the current budget scenario is ready for stakeholder review."""

    rows = [
        _history_check(weekly_rows),
        _holdout_check(float(mmm_result.metrics["test_mape"])),
        _profit_check(float(scenario.summary.get("weekly_profit_change_gbp", 0.0))),
        _spend_change_check(float(scenario.summary.get("spend_change_pct", 0.0))),
        _evidence_check(evidence_quality),
    ]
    checks = pd.DataFrame(rows, columns=["check", "status", "detail", "required_action"])
    score = _readiness_score(checks)
    status = _overall_status(checks, score)
    required_actions = [
        str(action)
        for action in checks["required_action"].tolist()
        if str(action).strip() and str(action) != "None"
    ]
    return RecommendationReadiness(
        status=status,
        score=score,
        checks=checks,
        required_actions=required_actions,
    )


def _history_check(weekly_rows: int) -> dict[str, str]:
    if weekly_rows >= 104:
        return _row("Modeling history", "Pass", f"{weekly_rows} weekly rows available.", "None")
    if weekly_rows >= 57:
        return _row(
            "Modeling history",
            "Review",
            f"{weekly_rows} weekly rows meet the current minimum but remain short for robust MMM.",
            "Treat the recommendation as directional until more history is available.",
        )
    return _row(
        "Modeling history",
        "Block",
        f"{weekly_rows} weekly rows are below the current modeling minimum.",
        "Do not advance until at least 57 continuous weekly rows are available.",
    )


def _holdout_check(test_mape: float) -> dict[str, str]:
    if test_mape <= 0.15:
        return _row("Holdout accuracy", "Pass", f"Holdout MAPE is {_pct(test_mape)}.", "None")
    if test_mape <= 0.25:
        return _row(
            "Holdout accuracy",
            "Review",
            f"Holdout MAPE is {_pct(test_mape)}.",
            "Review residuals and sensitivity before presenting a recommendation.",
        )
    return _row(
        "Holdout accuracy",
        "Block",
        f"Holdout MAPE is {_pct(test_mape)}.",
        "Do not advance until model fit is improved or the limitation is explicitly accepted.",
    )


def _profit_check(weekly_profit_change_gbp: float) -> dict[str, str]:
    if weekly_profit_change_gbp > 0:
        return _row(
            "Profit impact",
            "Pass",
            f"Scenario estimates positive weekly profit impact of {_gbp(weekly_profit_change_gbp)}.",
            "None",
        )
    if abs(weekly_profit_change_gbp) < 1e-6:
        return _row(
            "Profit impact",
            "Review",
            "Scenario is broadly neutral on weekly profit.",
            "Clarify why a neutral scenario is worth stakeholder review.",
        )
    return _row(
        "Profit impact",
        "Block",
        f"Scenario estimates weekly profit decline of {_gbp(abs(weekly_profit_change_gbp))}.",
        "Revise allocation before advancing.",
    )


def _spend_change_check(spend_change_pct: float) -> dict[str, str]:
    absolute_change = abs(spend_change_pct)
    if absolute_change <= 0.20:
        return _row(
            "Spend movement",
            "Pass",
            f"Weekly spend changes by {_pct(spend_change_pct)}.",
            "None",
        )
    if absolute_change <= 0.35:
        return _row(
            "Spend movement",
            "Review",
            f"Weekly spend changes by {_pct(spend_change_pct)}.",
            "Confirm channel capacity, pacing, and campaign availability.",
        )
    return _row(
        "Spend movement",
        "Block",
        f"Weekly spend changes by {_pct(spend_change_pct)}.",
        "Reduce the proposed movement or document an explicit launch plan.",
    )


def _evidence_check(evidence_quality: pd.DataFrame | None) -> dict[str, str]:
    if evidence_quality is None or evidence_quality.empty:
        return _row(
            "Experiment evidence",
            "Review",
            "No experiment evidence is available for this run.",
            "Use the recommendation as directional until incrementality evidence is added.",
        )

    approved = evidence_quality[evidence_quality["approved_for_calibration"]]
    strong_or_usable = approved[approved["quality_tier"].isin(["Strong", "Usable"])]
    if not strong_or_usable.empty:
        return _row(
            "Experiment evidence",
            "Pass",
            f"{len(strong_or_usable)} approved usable experiment rows are available.",
            "None",
        )
    if not approved.empty:
        return _row(
            "Experiment evidence",
            "Review",
            f"{len(approved)} approved experiment rows are available but quality needs review.",
            "Review evidence quality before relying on calibration.",
        )
    return _row(
        "Experiment evidence",
        "Review",
        "Experiment evidence exists, but no rows are approved for calibration.",
        "Seek approval or use the recommendation as directional only.",
    )


def _readiness_score(checks: pd.DataFrame) -> float:
    weights = {"Pass": 1.0, "Review": 0.5, "Block": 0.0}
    return round(float(checks["status"].map(weights).mean() * 100), 1)


def _overall_status(checks: pd.DataFrame, score: float) -> str:
    if (checks["status"] == "Block").any():
        return "Do not advance"
    critical_checks = checks[checks["check"].isin(["Profit impact", "Experiment evidence"])]
    if score >= 80 and critical_checks["status"].eq("Pass").all():
        return "Candidate for stakeholder review"
    return "Needs analyst review"


def _row(check: str, status: str, detail: str, required_action: str) -> dict[str, str]:
    return {
        "check": check,
        "status": status,
        "detail": detail,
        "required_action": required_action,
    }


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
