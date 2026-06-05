"""Experiment calibration helpers for MMM outputs."""

from __future__ import annotations

from io import StringIO

import pandas as pd

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS
from marketing_effectiveness_lab.mmm import MmmModelResult
from marketing_effectiveness_lab.uncertainty import MmmUncertaintyResult

REQUIRED_LIFT_TEST_COLUMNS = {
    "channel",
    "experiment_type",
    "weeks",
    "model_lift_gbp",
    "observed_lift_gbp",
    "observed_lift_lower_gbp",
    "observed_lift_upper_gbp",
}

OPTIONAL_LIFT_TEST_COLUMNS = [
    "test_name",
    "start_date",
    "end_date",
    "market",
    "confidence_level",
    "approval_status",
    "owner",
    "source_notes",
]

APPROVED_STATUSES = {"approved", "approved for calibration"}


def demo_lift_test_calibrations(mmm_result: MmmModelResult) -> pd.DataFrame:
    """Create deterministic demo lift-test readouts from an MMM contribution table."""

    contribution = mmm_result.contribution_table.set_index("channel")
    experiment_plan = [
        {
            "channel": "Paid search",
            "experiment_type": "Geo holdout",
            "weeks": 6,
            "lift_share": 0.20,
            "factor": 0.96,
            "interval_pct": 0.16,
        },
        {
            "channel": "Paid social",
            "experiment_type": "Conversion lift",
            "weeks": 4,
            "lift_share": 0.18,
            "factor": 1.15,
            "interval_pct": 0.22,
        },
        {
            "channel": "Display",
            "experiment_type": "Matched-market test",
            "weeks": 8,
            "lift_share": 0.22,
            "factor": 0.82,
            "interval_pct": 0.24,
        },
        {
            "channel": "Influencer",
            "experiment_type": "Brand-search lift",
            "weeks": 5,
            "lift_share": 0.16,
            "factor": 1.10,
            "interval_pct": 0.28,
        },
    ]

    rows = []
    for experiment in experiment_plan:
        channel = experiment["channel"]
        if channel not in contribution.index:
            continue
        avg_contribution = float(contribution.loc[channel, "avg_weekly_contribution_gbp"])
        model_lift = max(avg_contribution * experiment["weeks"] * experiment["lift_share"], 1.0)
        observed_lift = model_lift * experiment["factor"]
        interval = observed_lift * experiment["interval_pct"]
        rows.append(
            {
                "channel": channel,
                "experiment_type": experiment["experiment_type"],
                "weeks": experiment["weeks"],
                "model_lift_gbp": model_lift,
                "observed_lift_gbp": observed_lift,
                "observed_lift_lower_gbp": max(observed_lift - interval, 0.0),
                "observed_lift_upper_gbp": observed_lift + interval,
                "approval_status": "Approved",
            }
        )

    lift_tests = pd.DataFrame(rows)
    lift_tests["calibration_factor"] = lift_tests["observed_lift_gbp"] / lift_tests["model_lift_gbp"]
    return lift_tests


def lift_test_template_dataframe() -> pd.DataFrame:
    """Return a small lift-test CSV template for real experiment evidence."""

    return pd.DataFrame(
        [
            {
                "test_name": "Paid search geo holdout",
                "channel": "Paid search",
                "experiment_type": "Geo holdout",
                "start_date": "2025-04-07",
                "end_date": "2025-05-18",
                "weeks": 6,
                "market": "UK regions",
                "model_lift_gbp": 250000,
                "observed_lift_gbp": 240000,
                "observed_lift_lower_gbp": 200000,
                "observed_lift_upper_gbp": 280000,
                "confidence_level": 0.90,
                "approval_status": "Approved",
                "owner": "Marketing analytics",
                "source_notes": "Matched regions using pre-period revenue and spend.",
            },
            {
                "test_name": "Paid social conversion lift",
                "channel": "Paid social",
                "experiment_type": "Conversion lift",
                "start_date": "2025-06-02",
                "end_date": "2025-06-29",
                "weeks": 4,
                "market": "UK prospecting audience",
                "model_lift_gbp": 180000,
                "observed_lift_gbp": 205000,
                "observed_lift_lower_gbp": 160000,
                "observed_lift_upper_gbp": 250000,
                "confidence_level": 0.90,
                "approval_status": "Approved",
                "owner": "Growth team",
                "source_notes": "Platform conversion-lift readout reconciled to revenue.",
            },
        ]
    )


def lift_test_template_csv() -> str:
    """Return a downloadable lift-test CSV template."""

    return lift_test_template_dataframe().to_csv(index=False)


def validate_lift_test_csv_text(csv_text: str) -> tuple[pd.DataFrame | None, list[str]]:
    """Parse and validate lift-test CSV text."""

    try:
        lift_tests = pd.read_csv(StringIO(csv_text))
    except Exception as exc:  # pragma: no cover - parser wording varies by pandas version.
        return None, [f"CSV could not be parsed: {exc}"]

    lift_tests = _coerce_lift_test_types(lift_tests)
    errors = validate_lift_tests(lift_tests)
    if errors:
        return None, errors

    if "calibration_factor" not in lift_tests.columns:
        lift_tests["calibration_factor"] = (
            lift_tests["observed_lift_gbp"] / lift_tests["model_lift_gbp"]
        )
    return lift_tests, []


def assess_lift_test_evidence(lift_tests: pd.DataFrame) -> pd.DataFrame:
    """Score lift-test evidence quality and generate review flags."""

    errors = validate_lift_tests(lift_tests)
    if errors:
        raise ValueError(" ".join(errors))

    assessed = _coerce_lift_test_types(lift_tests).copy()
    if "calibration_factor" not in assessed.columns:
        assessed["calibration_factor"] = assessed["observed_lift_gbp"] / assessed["model_lift_gbp"]

    assessed["interval_width_pct"] = (
        (assessed["observed_lift_upper_gbp"] - assessed["observed_lift_lower_gbp"])
        / assessed["observed_lift_gbp"]
    ).clip(lower=0)
    assessed["metadata_completeness"] = _metadata_completeness(assessed)

    duration_score = (assessed["weeks"] / 6).clip(upper=1.0)
    precision_score = (1 - assessed["interval_width_pct"] / 0.80).clip(lower=0.0, upper=1.0)
    calibration_score = (1 - (assessed["calibration_factor"] - 1).abs() / 1.25).clip(
        lower=0.0,
        upper=1.0,
    )
    assessed["evidence_quality_score"] = (
        100
        * (
            0.30 * duration_score
            + 0.35 * precision_score
            + 0.20 * assessed["metadata_completeness"]
            + 0.15 * calibration_score
        )
    ).round(1)
    assessed["quality_tier"] = assessed["evidence_quality_score"].map(_quality_tier)
    assessed["review_flags"] = assessed.apply(_review_flags, axis=1)
    assessed["approval_status"] = assessed.get("approval_status", "Needs review")
    assessed["approved_for_calibration"] = assessed["approval_status"].map(_is_approved_status)

    return assessed.sort_values(
        ["approved_for_calibration", "evidence_quality_score"],
        ascending=[False, False],
    ).reset_index(drop=True)


def approved_lift_tests(lift_tests: pd.DataFrame) -> pd.DataFrame:
    """Return only evidence rows approved for calibration, preserving fallback behavior."""

    assessed = assess_lift_test_evidence(lift_tests)
    approved = assessed[assessed["approved_for_calibration"]].copy()
    return approved.reset_index(drop=True)


def validate_lift_tests(lift_tests: pd.DataFrame) -> list[str]:
    """Validate lift-test rows before applying them to MMM output."""

    errors: list[str] = []
    missing = sorted(REQUIRED_LIFT_TEST_COLUMNS - set(lift_tests.columns))
    if missing:
        errors.append(f"Missing required lift-test columns: {', '.join(missing)}.")
        return errors

    lift_tests = _coerce_lift_test_types(lift_tests)
    known_channels = set(CHANNEL_LABELS.values())
    unknown_channels = sorted(set(lift_tests["channel"].dropna()) - known_channels)
    if unknown_channels:
        errors.append(f"Unknown channel labels: {', '.join(unknown_channels)}.")

    numeric_columns = [
        "weeks",
        "model_lift_gbp",
        "observed_lift_gbp",
        "observed_lift_lower_gbp",
        "observed_lift_upper_gbp",
    ]
    if "confidence_level" in lift_tests.columns:
        numeric_columns.append("confidence_level")
    for column in numeric_columns:
        if lift_tests[column].isna().any():
            errors.append(f"{column} contains missing values.")

    positive_columns = ["weeks", "model_lift_gbp", "observed_lift_gbp"]
    for column in positive_columns:
        if (lift_tests[column] <= 0).any():
            errors.append(f"{column} must be positive.")

    if (lift_tests["observed_lift_lower_gbp"] < 0).any():
        errors.append("observed_lift_lower_gbp cannot be negative.")
    if (lift_tests["observed_lift_lower_gbp"] > lift_tests["observed_lift_gbp"]).any():
        errors.append("observed_lift_lower_gbp cannot exceed observed_lift_gbp.")
    if (lift_tests["observed_lift_upper_gbp"] < lift_tests["observed_lift_gbp"]).any():
        errors.append("observed_lift_upper_gbp cannot be below observed_lift_gbp.")
    if "confidence_level" in lift_tests.columns:
        if ((lift_tests["confidence_level"] <= 0) | (lift_tests["confidence_level"] >= 1)).any():
            errors.append("confidence_level must be greater than 0 and less than 1.")
    if "approval_status" in lift_tests.columns:
        if lift_tests["approval_status"].isna().any():
            errors.append("approval_status contains missing values.")

    return errors


def calibration_factors(
    lift_tests: pd.DataFrame,
    min_factor: float = 0.25,
    max_factor: float = 2.00,
) -> pd.DataFrame:
    """Calculate channel-level calibration factors from lift-test readouts."""

    errors = validate_lift_tests(lift_tests)
    if errors:
        raise ValueError(" ".join(errors))
    if min_factor <= 0 or max_factor <= min_factor:
        raise ValueError("Calibration bounds must be positive and ordered.")

    grouped = (
        lift_tests.groupby("channel", as_index=False)
        .agg(
            model_lift_gbp=("model_lift_gbp", "sum"),
            observed_lift_gbp=("observed_lift_gbp", "sum"),
            observed_lift_lower_gbp=("observed_lift_lower_gbp", "sum"),
            observed_lift_upper_gbp=("observed_lift_upper_gbp", "sum"),
            evidence_weeks=("weeks", "sum"),
            experiments=("experiment_type", "count"),
        )
        .sort_values("channel")
    )
    grouped["raw_calibration_factor"] = grouped["observed_lift_gbp"] / grouped["model_lift_gbp"]
    grouped["calibration_factor"] = grouped["raw_calibration_factor"].clip(min_factor, max_factor)
    grouped["calibration_lower"] = (
        grouped["observed_lift_lower_gbp"] / grouped["model_lift_gbp"]
    ).clip(min_factor, max_factor)
    grouped["calibration_upper"] = (
        grouped["observed_lift_upper_gbp"] / grouped["model_lift_gbp"]
    ).clip(min_factor, max_factor)
    return grouped[
        [
            "channel",
            "raw_calibration_factor",
            "calibration_factor",
            "calibration_lower",
            "calibration_upper",
            "evidence_weeks",
            "experiments",
        ]
    ].reset_index(drop=True)


def apply_lift_calibration(contribution_table: pd.DataFrame, lift_tests: pd.DataFrame) -> pd.DataFrame:
    """Apply experiment calibration factors to an MMM contribution table."""

    factors = calibration_factors(lift_tests)
    calibrated = contribution_table.merge(factors, on="channel", how="left")
    for column in [
        "raw_calibration_factor",
        "calibration_factor",
        "calibration_lower",
        "calibration_upper",
    ]:
        calibrated[column] = calibrated[column].fillna(1.0)
    calibrated["evidence_weeks"] = calibrated["evidence_weeks"].fillna(0).astype(int)
    calibrated["experiments"] = calibrated["experiments"].fillna(0).astype(int)
    calibrated["calibration_status"] = calibrated["experiments"].map(
        lambda value: "Experiment-calibrated" if value > 0 else "Uncalibrated"
    )
    calibrated["estimated_contribution_calibrated_gbp"] = (
        calibrated["estimated_contribution_gbp"] * calibrated["calibration_factor"]
    )
    calibrated["estimated_roi_calibrated"] = calibrated["estimated_contribution_calibrated_gbp"] / calibrated[
        "spend_gbp"
    ].replace(0, pd.NA)
    calibrated["estimated_roi_calibrated"] = calibrated["estimated_roi_calibrated"].fillna(0.0)
    return calibrated.sort_values("estimated_contribution_calibrated_gbp", ascending=False).reset_index(drop=True)


def apply_lift_calibration_to_intervals(
    uncertainty: MmmUncertaintyResult,
    lift_tests: pd.DataFrame,
) -> pd.DataFrame:
    """Apply lift-test calibration factors to contribution uncertainty intervals."""

    factors = calibration_factors(lift_tests)
    intervals = uncertainty.contribution_intervals.merge(factors, on="channel", how="left")
    for column in ["calibration_factor", "calibration_lower", "calibration_upper"]:
        intervals[column] = intervals[column].fillna(1.0)
    intervals["experiments"] = intervals["experiments"].fillna(0).astype(int)
    intervals["calibration_status"] = intervals["experiments"].map(
        lambda value: "Experiment-calibrated" if value > 0 else "Uncalibrated"
    )
    intervals["contribution_mean_calibrated_gbp"] = (
        intervals["contribution_mean_gbp"] * intervals["calibration_factor"]
    )
    intervals["contribution_lower_calibrated_gbp"] = (
        intervals["contribution_lower_gbp"] * intervals["calibration_lower"]
    )
    intervals["contribution_upper_calibrated_gbp"] = (
        intervals["contribution_upper_gbp"] * intervals["calibration_upper"]
    )
    intervals["roi_mean_calibrated"] = intervals["contribution_mean_calibrated_gbp"] / intervals[
        "spend_gbp"
    ].replace(0, pd.NA)
    intervals["roi_lower_calibrated"] = intervals["contribution_lower_calibrated_gbp"] / intervals[
        "spend_gbp"
    ].replace(0, pd.NA)
    intervals["roi_upper_calibrated"] = intervals["contribution_upper_calibrated_gbp"] / intervals[
        "spend_gbp"
    ].replace(0, pd.NA)
    return intervals.fillna(0.0).sort_values(
        "contribution_mean_calibrated_gbp",
        ascending=False,
    )


def _coerce_lift_test_types(lift_tests: pd.DataFrame) -> pd.DataFrame:
    typed = lift_tests.copy()
    for column in [
        "weeks",
        "model_lift_gbp",
        "observed_lift_gbp",
        "observed_lift_lower_gbp",
        "observed_lift_upper_gbp",
        "confidence_level",
    ]:
        if column in typed.columns:
            typed[column] = pd.to_numeric(typed[column], errors="coerce")
    for column in ["start_date", "end_date"]:
        if column in typed.columns:
            typed[column] = pd.to_datetime(typed[column], errors="coerce").dt.strftime("%Y-%m-%d")
    if "approval_status" in typed.columns:
        typed["approval_status"] = typed["approval_status"].fillna("").astype(str).str.strip()
    return typed


def _metadata_completeness(lift_tests: pd.DataFrame) -> pd.Series:
    metadata_columns = [
        column
        for column in ["test_name", "start_date", "end_date", "market", "owner", "source_notes"]
        if column in lift_tests.columns
    ]
    if not metadata_columns:
        return pd.Series(0.0, index=lift_tests.index)
    present = lift_tests[metadata_columns].notna() & (lift_tests[metadata_columns].astype(str) != "")
    return present.mean(axis=1)


def _quality_tier(score: float) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Usable"
    return "Needs review"


def _review_flags(row: pd.Series) -> str:
    flags = []
    if row["weeks"] < 4:
        flags.append("Short test")
    if row["interval_width_pct"] > 0.60:
        flags.append("Wide interval")
    if row["calibration_factor"] < 0.50 or row["calibration_factor"] > 1.75:
        flags.append("Large MMM mismatch")
    if row["metadata_completeness"] < 0.50:
        flags.append("Sparse metadata")
    if not flags:
        return "No major flags"
    return "; ".join(flags)


def _is_approved_status(status: object) -> bool:
    return str(status).strip().lower() in APPROVED_STATUSES
