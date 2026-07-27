"""Audit tool: freeze a metric-bearing function and see whether the test suite notices.

A test suite can be large, green and still not check that anything is computed. The
cheapest way to find out is to break the code on purpose: replace a function with a stub
that returns a constant of the right shape and dtype, then run the suite. Whatever stays
green is a test that measures that the code *ran*, not that it computed anything.

This repo failed that check once. Freezing ``analytics.summarize_kpis``,
``channel_summary`` and ``promotion_summary`` produced zero red tests: the assertions
were ``> 0``, column-name sets and row counts, all of which a constant satisfies.
``tests/test_metric_sensitivity.py`` exists to close that gap, and this script is how the
gap was found and how a future change should be re-checked.

One function is frozen per run, and the result is reported per function rather than per
group. That matters: an earlier version of this tool froze three functions together and
reported a single "3 detected", which hid the fact that one of the three was still
completely undetected.

    uv run python scripts/sabotage_sweep.py                       # every target, ~1 run each
    uv run python scripts/sabotage_sweep.py --target mmm.hill_saturation

A full sweep runs the suite once per target, so it takes a few minutes. **A target with
zero detections is a finding, not a pass.**
"""

from __future__ import annotations

import argparse
import dataclasses as dc
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _const_like(values: object, fill: float) -> np.ndarray:
    raw = np.asarray(values, dtype=float)
    return np.full(raw.shape, fill, dtype=float)


def _freeze_numeric_columns(frame: pd.DataFrame, fill: float = 1.0) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        if pd.api.types.is_numeric_dtype(out[column]):
            out[column] = fill
    return out


def _freeze_numeric_values(payload: dict[str, object], fill: float = 1.0) -> dict[str, object]:
    """Freeze the numbers in a summary dict, leaving labels and flags alone."""

    return {
        key: (fill if isinstance(value, (int, float)) and not isinstance(value, bool) else value)
        for key, value in payload.items()
    }


def _patch_everywhere(real_fn: object, frozen: object) -> None:
    """Rebind every alias of ``real_fn`` inside the package, not just its defining module.

    Consumers do ``from marketing_effectiveness_lab.mmm import hill_saturation``, which
    binds the function object by value. Patching only the defining module leaves those
    consumers running the real code, and the sweep would then credit coverage that does
    not exist.
    """

    for module in list(sys.modules.values()):
        name = getattr(module, "__name__", "")
        if not name.startswith("marketing_effectiveness_lab"):
            continue
        for attribute, value in list(vars(module).items()):
            if value is real_fn:
                setattr(module, attribute, frozen)


def _freeze_frame_result(module: object, name: str) -> None:
    real = getattr(module, name)

    def frozen(*args: object, **kwargs: object) -> object:
        out = real(*args, **kwargs)
        return _freeze_numeric_columns(out) if isinstance(out, pd.DataFrame) else out

    _patch_everywhere(real, frozen)


def _freeze_result_object(
    module: object,
    name: str,
    frame_fields: tuple[str, ...],
    dict_fields: tuple[str, ...] = (),
) -> None:
    real = getattr(module, name)

    def frozen(*args: object, **kwargs: object) -> object:
        out = real(*args, **kwargs)
        changes: dict[str, object] = {}
        for field in frame_fields:
            value = getattr(out, field, None)
            if isinstance(value, pd.DataFrame):
                changes[field] = _freeze_numeric_columns(value)
        for field in dict_fields:
            value = getattr(out, field, None)
            if isinstance(value, dict):
                changes[field] = _freeze_numeric_values(value)
        return dc.replace(out, **changes)

    _patch_everywhere(real, frozen)


def _build_targets() -> dict[str, Callable[[], None]]:
    from marketing_effectiveness_lab import (
        analytics,
        budget,
        calibration,
        customer,
        mmm,
        modeling,
        uncertainty,
    )

    def freeze_prepare_weekly_frame() -> None:
        real = analytics.prepare_weekly_frame
        derived = ["total_media_spend_gbp", "blended_roas", "revenue_4w_avg", "media_spend_4w_avg"]

        def frozen(df: pd.DataFrame) -> pd.DataFrame:
            out = real(df)
            for column in derived:
                out[column] = 1.0
            return out

        _patch_everywhere(real, frozen)

    def freeze_summarize_kpis() -> None:
        real = analytics.summarize_kpis
        _patch_everywhere(
            real,
            lambda df: analytics.KpiSummary(
                revenue_gbp=1.0,
                media_spend_gbp=1.0,
                orders=1,
                new_customers=1,
                average_order_value_gbp=1.0,
                blended_roas=1.0,
            ),
        )

    def freeze_optimize_budget_allocation() -> None:
        real = budget.optimize_budget_allocation

        def frozen(*args: object, **kwargs: object) -> object:
            out = real(*args, **kwargs)
            total = sum(out.allocation.values())
            equal = total / len(out.allocation) if out.allocation else 0.0
            return dc.replace(
                out,
                allocation=dict.fromkeys(out.allocation, equal),
                diagnostics=_freeze_numeric_columns(out.diagnostics),
                summary=_freeze_numeric_values(out.summary),
            )

        _patch_everywhere(real, frozen)

    return {
        "analytics.prepare_weekly_frame": freeze_prepare_weekly_frame,
        "analytics.summarize_kpis": freeze_summarize_kpis,
        "analytics.channel_summary": lambda: _freeze_frame_result(analytics, "channel_summary"),
        "analytics.promotion_summary": lambda: _freeze_frame_result(analytics, "promotion_summary"),
        "mmm.geometric_adstock": lambda: _patch_everywhere(
            mmm.geometric_adstock, lambda values, decay: _const_like(values, 1.0)
        ),
        "mmm.hill_saturation": lambda: _patch_everywhere(
            mmm.hill_saturation, lambda values, half_saturation, slope: _const_like(values, 0.5)
        ),
        "mmm.fit_mmm_foundation_model": lambda: _freeze_result_object(
            mmm,
            "fit_mmm_foundation_model",
            ("train_frame", "test_frame", "contribution_table", "response_curves"),
            ("metrics",),
        ),
        "modeling.fit_baseline_model": lambda: _freeze_result_object(
            modeling,
            "fit_baseline_model",
            ("train_frame", "test_frame", "coefficient_table", "vif_table"),
            ("metrics",),
        ),
        "uncertainty.simulate_mmm_uncertainty": lambda: _freeze_result_object(
            uncertainty,
            "simulate_mmm_uncertainty",
            ("contribution_intervals", "prediction_intervals"),
        ),
        "budget.evaluate_budget_scenario": lambda: _freeze_result_object(
            budget, "evaluate_budget_scenario", ("channel_table",), ("summary",)
        ),
        "budget.optimize_budget_allocation": freeze_optimize_budget_allocation,
        "customer.customer_future_value_backtest": lambda: _freeze_frame_result(
            customer, "customer_future_value_backtest"
        ),
        "customer.cohort_retention": lambda: _freeze_frame_result(customer, "cohort_retention"),
        "calibration.calibration_factors": lambda: _freeze_frame_result(calibration, "calibration_factors"),
    }


def pytest_configure(config: object) -> None:
    """Entry point when this module is loaded as a pytest plugin (`-p sabotage_sweep`)."""

    target = os.environ.get("SABOTAGE", "")
    if not target:
        return
    targets = _build_targets()
    if target not in targets:
        raise SystemExit(f"unknown sabotage target {target!r}; choose one of {sorted(targets)}")
    targets[target]()
    print(f"\n[sabotage active: {target}]")


def _parse_counts(stdout: str) -> tuple[int, int]:
    """Return (detected, survived) from pytest's summary line.

    Errors count as detections: a test that blows up under sabotage has noticed, even
    though it did not fail an assertion.
    """

    lines = [line for line in stdout.splitlines() if " passed" in line or " failed" in line or " error" in line]
    if not lines:
        raise RuntimeError("could not find a pytest summary line in the output")
    summary = lines[-1]

    def count(label: str) -> int:
        tokens = summary.replace(",", "").split()
        for index, token in enumerate(tokens):
            if token.startswith(label) and index > 0:
                try:
                    return int(tokens[index - 1])
                except ValueError:
                    return 0
        return 0

    return count("failed") + count("error"), count("passed")


def _run_target(target: str) -> tuple[int, int]:
    env = dict(os.environ)
    env["SABOTAGE"] = target
    scripts_dir = str(PROJECT_ROOT / "scripts")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [scripts_dir, env.get("PYTHONPATH", "")]))
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "sabotage_sweep", "--tb=no"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    # pytest: 0 = all passed, 1 = tests failed. Anything else (2 usage, 3 internal,
    # 4 usage, 5 no tests) means the run itself broke, and reporting that as "blind"
    # would be the tool inventing its own strongest finding.
    if completed.returncode not in {0, 1}:
        raise RuntimeError(
            f"pytest exited {completed.returncode} for target {target}:\n"
            f"{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}"
        )
    return _parse_counts(completed.stdout)


def main() -> None:
    targets = sorted(_build_targets())
    parser = argparse.ArgumentParser(description="Freeze metric-bearing functions and report detection.")
    parser.add_argument("--target", choices=targets, help="Freeze a single function instead of all.")
    args = parser.parse_args()

    selected = [args.target] if args.target else targets
    print(f"{'frozen function':<42} {'detected':>9} {'survived':>9}  verdict")
    blind = []
    for target in selected:
        detected, survived = _run_target(target)
        if detected == 0:
            blind.append(target)
        verdict = "BLIND - no test noticed" if detected == 0 else "noticed"
        print(f"{target:<42} {detected:>9} {survived:>9}  {verdict}")

    if blind:
        print("\nBlind paths (add a test to tests/test_metric_sensitivity.py):")
        for target in blind:
            print(f"  - {target}")
        raise SystemExit(1)
    print("\nEvery frozen function was detected by at least one test.")


if __name__ == "__main__":
    main()
