from __future__ import annotations

import math

import pandas as pd
import pytest

from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.modeling import _mape, fit_baseline_model, make_model_frame


def test_mape_ignores_zero_actuals() -> None:
    actual = pd.Series([0.0, 100.0, 200.0])
    predicted = pd.Series([10.0, 110.0, 180.0])

    result = _mape(actual, predicted)

    # The zero actual is excluded rather than producing inf/NaN.
    assert math.isfinite(result)
    assert result == pytest.approx((0.10 + 0.10) / 2)


def test_make_model_frame_adds_expected_features() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    model_df = make_model_frame(df)

    assert "log_revenue_gbp" in model_df.columns
    assert "log_paid_search_spend_gbp" in model_df.columns
    assert "log_organic_search_sessions" in model_df.columns
    assert "trend_squared" in model_df.columns


def test_baseline_model_returns_diagnostics() -> None:
    df, _ = generate_weekly_demo_data(seed=42)
    result = fit_baseline_model(df, holdout_weeks=26)

    assert len(result.train_frame) == len(df) - 26
    assert len(result.test_frame) == 26
    assert result.metrics["train_r_squared"] > 0.75
    assert result.metrics["test_mape"] < 0.2
    assert not result.coefficient_table.empty
    assert not result.vif_table.empty


def test_baseline_model_rejects_tiny_data() -> None:
    df, _ = generate_weekly_demo_data(seed=42)

    with pytest.raises(ValueError, match="Not enough rows"):
        fit_baseline_model(df.head(40), holdout_weeks=26)

