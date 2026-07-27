"""Audit tool: freeze the analytics and see whether the test suite notices.

A test suite can be large, green and still not check that anything is computed. The
cheapest way to find out is to break the code on purpose: replace metric-bearing
functions with stubs that return constants of the right shape and dtype, then run the
suite. Whatever stays green is a test that measures that the code *ran*, not that it
computed anything.

This repo failed that check once. Freezing ``analytics.summarize_kpis``,
``channel_summary`` and ``promotion_summary`` produced zero red tests: the assertions
were ``> 0``, column-name sets and row counts, all of which a constant satisfies.
``tests/test_metric_sensitivity.py`` exists to close that gap, and this script is how
the gap was found and how a future change should be re-checked.

Run it against the current tree:

    uv run python scripts/sabotage_sweep.py

Add ``--variant <name>`` to run one freeze instead of all of them. A variant that
produces no failures is a finding, not a pass.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VARIANTS = ("transforms", "mmm_outputs", "analytics", "customer", "dataclasses", "all")


def _const_like(values: object, fill: float) -> np.ndarray:
    raw = np.asarray(values, dtype=float)
    return np.full(raw.shape, fill, dtype=float)


def _freeze_numeric_columns(frame: pd.DataFrame, fill: float = 1.0) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        if pd.api.types.is_numeric_dtype(out[column]):
            out[column] = fill
    return out


def _freeze_frame_result(real_fn):
    def frozen(*args: object, **kwargs: object) -> object:
        out = real_fn(*args, **kwargs)
        return _freeze_numeric_columns(out) if isinstance(out, pd.DataFrame) else out

    return frozen


def _freeze_dataclass_result(real_fn, frame_fields: tuple[str, ...], dict_fields: tuple[str, ...] = ()):
    def frozen(*args: object, **kwargs: object) -> object:
        out = real_fn(*args, **kwargs)
        changes: dict[str, object] = {}
        for field in frame_fields:
            value = getattr(out, field, None)
            if isinstance(value, pd.DataFrame):
                changes[field] = _freeze_numeric_columns(value)
        for field in dict_fields:
            value = getattr(out, field, None)
            if isinstance(value, dict):
                changes[field] = dict.fromkeys(value, 1.0)
        return dataclasses.replace(out, **changes)

    return frozen


def apply_sabotage(variant: str) -> None:
    """Replace metric-bearing functions with shape-preserving constant stubs."""

    from marketing_effectiveness_lab import (
        analytics,
        budget,
        calibration,
        customer,
        mmm,
        modeling,
        uncertainty,
    )

    if variant in {"transforms", "all"}:
        mmm.geometric_adstock = lambda values, decay: _const_like(values, 1.0)
        mmm.hill_saturation = lambda values, half_saturation, slope: _const_like(values, 0.5)

    if variant in {"analytics", "all"}:
        analytics.summarize_kpis = lambda df: analytics.KpiSummary(
            revenue_gbp=1.0,
            media_spend_gbp=1.0,
            orders=1,
            new_customers=1,
            average_order_value_gbp=1.0,
            blended_roas=1.0,
        )
        analytics.channel_summary = _freeze_frame_result(analytics.channel_summary)
        analytics.promotion_summary = _freeze_frame_result(analytics.promotion_summary)

    if variant in {"mmm_outputs", "all"}:
        mmm.fit_mmm_foundation_model = _freeze_dataclass_result(
            mmm.fit_mmm_foundation_model,
            ("train_frame", "test_frame", "contribution_table", "response_curves"),
            ("metrics",),
        )

    if variant in {"customer", "all"}:
        for name in (
            "customer_future_value_backtest",
            "score_customer_lapse_value",
            "cohort_retention",
            "customer_value_windows",
            "acquisition_channel_quality",
            "segment_summary",
        ):
            setattr(customer, name, _freeze_frame_result(getattr(customer, name)))

    if variant in {"dataclasses", "all"}:
        modeling.fit_baseline_model = _freeze_dataclass_result(
            modeling.fit_baseline_model,
            ("train_frame", "test_frame", "coefficient_table", "vif_table"),
            ("metrics",),
        )
        uncertainty.simulate_mmm_uncertainty = _freeze_dataclass_result(
            uncertainty.simulate_mmm_uncertainty,
            ("contribution_intervals", "prediction_intervals"),
        )
        budget.evaluate_budget_scenario = _freeze_dataclass_result(
            budget.evaluate_budget_scenario, ("channel_table",), ("summary",)
        )

    if variant == "all":
        for name in ("calibration_factors", "apply_lift_calibration", "assess_lift_test_evidence"):
            setattr(calibration, name, _freeze_frame_result(getattr(calibration, name)))


def pytest_configure(config: object) -> None:  # noqa: ARG001
    """Entry point when this module is loaded as a pytest plugin (`-p sabotage_sweep`)."""

    variant = os.environ.get("SABOTAGE", "")
    if variant:
        apply_sabotage(variant)
        print(f"\n[sabotage active: {variant}]")


def _run_variant(variant: str) -> tuple[int, int]:
    env = {**os.environ, "SABOTAGE": variant, "PYTHONPATH": str(PROJECT_ROOT / "scripts")}
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-q", "-p", "sabotage_sweep", "--tb=no"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    tail = [line for line in completed.stdout.splitlines() if " passed" in line or " failed" in line]
    summary = tail[-1] if tail else ""
    failed = int(summary.split(" failed")[0].strip().split()[-1]) if "failed" in summary else 0
    passed = int(summary.split(" passed")[0].strip().split()[-1]) if "passed" in summary else 0
    return failed, passed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, help="Run a single freeze instead of all.")
    args = parser.parse_args()

    variants = [args.variant] if args.variant else list(VARIANTS)
    print(f"{'variant':<14} {'detected':>9} {'survived':>9}  verdict")
    for variant in variants:
        failed, passed = _run_variant(variant)
        verdict = "blind - no test noticed" if failed == 0 else "noticed"
        print(f"{variant:<14} {failed:>9} {passed:>9}  {verdict}")

    print(
        "\nA variant with zero detections means the suite cannot tell that path apart from a "
        "constant. Add a test to tests/test_metric_sensitivity.py and re-run."
    )


if __name__ == "__main__":
    main()
