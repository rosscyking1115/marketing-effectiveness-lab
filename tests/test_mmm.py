from __future__ import annotations

import numpy as np
import pytest

from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import (
    calibrate_mmm_parameters,
    DEFAULT_MEDIA_PARAMETERS,
    fit_mmm_foundation_model,
    geometric_adstock,
    hill_saturation,
    make_mmm_frame,
)


def test_geometric_adstock_carries_forward_signal() -> None:
    transformed = geometric_adstock(np.array([100.0, 0.0, 0.0]), decay=0.5)

    assert transformed.tolist() == [100.0, 50.0, 25.0]


def test_hill_saturation_is_bounded_and_monotonic() -> None:
    values = np.array([0.0, 50.0, 100.0, 200.0])
    transformed = hill_saturation(values, half_saturation=100.0, slope=1.5)

    assert transformed.min() >= 0
    assert transformed.max() <= 1
    assert transformed.tolist() == sorted(transformed.tolist())


def test_make_mmm_frame_adds_media_features() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    mmm_df = make_mmm_frame(df)

    assert "paid_search_spend_gbp_adstocked" in mmm_df.columns
    assert "paid_search_spend_gbp_mmm" in mmm_df.columns
    assert mmm_df["paid_search_spend_gbp_mmm"].between(0, 1).all()


def test_mmm_foundation_model_returns_contribution_outputs() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    result = fit_mmm_foundation_model(df, holdout_weeks=26)

    assert len(result.train_frame) == len(df) - 26
    assert len(result.test_frame) == 26
    assert result.metrics["train_r_squared"] > 0.75
    assert result.metrics["test_mape"] < 0.2
    assert len(result.contribution_table) == 6
    assert len(result.parameter_table) == 6
    assert result.response_curves["channel"].nunique() == 6
    assert (result.contribution_table["estimated_roi"] >= 0).all()
    assert result.media_parameters["paid_search_spend_gbp"]["adstock_decay"] == 0.25


def test_mmm_foundation_model_accepts_custom_parameters() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    custom_parameters = {
        channel: params.copy() for channel, params in DEFAULT_MEDIA_PARAMETERS.items()
    }
    custom_parameters["paid_search_spend_gbp"]["adstock_decay"] = 0.7

    result = fit_mmm_foundation_model(
        df,
        holdout_weeks=26,
        media_parameters=custom_parameters,
    )

    assert result.media_parameters["paid_search_spend_gbp"]["adstock_decay"] == 0.7
    assert len(result.parameter_table) == 6


def test_calibrate_mmm_parameters_returns_search_results() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    calibration = calibrate_mmm_parameters(
        df,
        holdout_weeks=26,
        validation_weeks=16,
        decay_candidates=(0.1, 0.5),
        half_saturation_multipliers=(0.8, 1.2),
    )

    assert len(calibration.best_parameters) == 6
    assert len(calibration.search_table) == 24
    assert calibration.search_table["validation_mape"].notna().all()
    assert calibration.mmm_result.metrics["test_mape"] < 0.2


def test_mmm_foundation_model_rejects_tiny_data() -> None:
    df, _ = generate_weekly_demo_data(seed=42)

    with pytest.raises(ValueError, match="Not enough rows"):
        fit_mmm_foundation_model(df.head(40), holdout_weeks=26)
