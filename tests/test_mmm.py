from __future__ import annotations

import numpy as np
import pytest

from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import (
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


def test_mmm_foundation_model_rejects_tiny_data() -> None:
    df, _ = generate_weekly_demo_data(seed=42)

    with pytest.raises(ValueError, match="Not enough rows"):
        fit_mmm_foundation_model(df.head(40), holdout_weeks=26)

