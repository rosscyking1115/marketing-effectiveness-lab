from __future__ import annotations

import pandas as pd
import pytest

from marketing_effectiveness_lab.calibration import (
    apply_lift_calibration,
    apply_lift_calibration_to_intervals,
    calibration_factors,
    demo_lift_test_calibrations,
    validate_lift_tests,
)
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model
from marketing_effectiveness_lab.uncertainty import simulate_mmm_uncertainty


def test_demo_lift_tests_generate_valid_calibration_rows() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    lift_tests = demo_lift_test_calibrations(mmm_result)

    assert len(lift_tests) == 4
    assert validate_lift_tests(lift_tests) == []
    assert set(lift_tests["channel"]) == {"Paid search", "Paid social", "Display", "Influencer"}
    assert (lift_tests["calibration_factor"] > 0).all()


def test_calibration_factors_aggregate_duplicate_channel_tests() -> None:
    lift_tests = pd.DataFrame(
        [
            {
                "channel": "Paid search",
                "experiment_type": "Geo holdout",
                "weeks": 4,
                "model_lift_gbp": 100.0,
                "observed_lift_gbp": 120.0,
                "observed_lift_lower_gbp": 90.0,
                "observed_lift_upper_gbp": 140.0,
            },
            {
                "channel": "Paid search",
                "experiment_type": "Conversion lift",
                "weeks": 2,
                "model_lift_gbp": 50.0,
                "observed_lift_gbp": 45.0,
                "observed_lift_lower_gbp": 30.0,
                "observed_lift_upper_gbp": 65.0,
            },
        ]
    )

    factors = calibration_factors(lift_tests)

    assert len(factors) == 1
    assert factors.loc[0, "calibration_factor"] == pytest.approx(1.1)
    assert factors.loc[0, "evidence_weeks"] == 6
    assert factors.loc[0, "experiments"] == 2


def test_apply_lift_calibration_marks_channels_without_experiments() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    lift_tests = demo_lift_test_calibrations(mmm_result)

    calibrated = apply_lift_calibration(mmm_result.contribution_table, lift_tests)

    assert len(calibrated) == 6
    assert "estimated_contribution_calibrated_gbp" in calibrated.columns
    assert "Uncalibrated" in set(calibrated["calibration_status"])
    assert "Experiment-calibrated" in set(calibrated["calibration_status"])
    assert (calibrated["estimated_roi_calibrated"] >= 0).all()


def test_apply_lift_calibration_to_intervals_adds_adjusted_columns() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)
    uncertainty = simulate_mmm_uncertainty(mmm_result, draws=50, seed=42)
    lift_tests = demo_lift_test_calibrations(mmm_result)

    calibrated = apply_lift_calibration_to_intervals(uncertainty, lift_tests)

    assert len(calibrated) == 6
    assert "contribution_mean_calibrated_gbp" in calibrated.columns
    assert (
        calibrated["contribution_lower_calibrated_gbp"]
        <= calibrated["contribution_upper_calibrated_gbp"]
    ).all()


def test_validate_lift_tests_rejects_unknown_channels_and_bad_bounds() -> None:
    invalid = pd.DataFrame(
        [
            {
                "channel": "Unknown",
                "experiment_type": "Geo holdout",
                "weeks": 4,
                "model_lift_gbp": 100.0,
                "observed_lift_gbp": 80.0,
                "observed_lift_lower_gbp": 90.0,
                "observed_lift_upper_gbp": 70.0,
            }
        ]
    )

    errors = validate_lift_tests(invalid)

    assert any("Unknown channel" in error for error in errors)
    assert any("cannot exceed" in error for error in errors)
    assert any("cannot be below" in error for error in errors)
