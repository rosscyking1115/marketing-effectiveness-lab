"""Validation study: can the calibration search recover the true adstock and saturation?

``scripts/validate_recovery.py`` answers a narrower question. It scores the recovered
channel *effect* and ROI while handing the model the true adstock decay and
half-saturation, because ``DEFAULT_MEDIA_PARAMETERS`` in ``mmm.py`` happens to equal the
generating ``media_specs``. That is a legitimate design — it isolates the identification
problem from transform misspecification — but it leaves the transform parameters
themselves untested.

This script tests them. It runs the same time-aware validation search used by
``calibrate_mmm_parameters``, but:

* the half-saturation grid is an absolute lattice (20k-200k in 20k steps), not a set of
  multipliers around the true value, so the truth is not sitting at the centre of the grid;
* the search starts from a neutral seed (decay 0.35, half-saturation 100k for every
  channel) rather than from the generating values;
* the recovered values are compared against the generated ground truth in
  ``data/demo/ground_truth_metadata.json`` — a file the generator has always written and
  nothing has ever read — falling back to the in-process truth when it is absent, since
  ``data/demo`` is git-ignored.

What is *not* recovered: the Hill slope is fixed at 1.35 in both the generator and the
model, so it is assumed, not tested. Grid search recovers to the nearest grid point, so
the reported error includes a known grid-resolution floor, printed alongside it.

Regenerate with:

    uv run python scripts/validate_transform_recovery.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS, spend_columns
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.mmm import calibrate_mmm_parameters, fit_mmm_foundation_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "demo" / "ground_truth_metadata.json"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "assets" / "validation"

SEED = 42
HOLDOUT_WEEKS = 26
VALIDATION_WEEKS = 20
SLOPE = 1.35

# Regular lattices, chosen for even coverage rather than to straddle the truth.
DECAY_CANDIDATES = (0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75)
HALF_SATURATION_CANDIDATES_GBP = tuple(float(value) for value in range(20_000, 200_001, 20_000))
NEUTRAL_DECAY = 0.35
NEUTRAL_HALF_SATURATION_GBP = 100_000.0


def load_ground_truth(df: pd.DataFrame, generated: dict[str, object]) -> dict[str, dict[str, float]]:
    """Prefer the on-disk ground-truth metadata, and refuse to score against a stale copy.

    ``data/demo/*.json`` is git-ignored, so the file only exists after
    ``scripts/generate_demo_data.py`` has been run. When it is there it is used and
    checked against the generator, which is the point: the file records the true
    adstock and saturation parameters and had no reader before this script. When it is
    absent the study falls back to the in-process ground truth so a fresh clone can
    still reproduce the result.
    """

    if not GROUND_TRUTH_PATH.exists():
        print(
            f"note: {GROUND_TRUTH_PATH.relative_to(PROJECT_ROOT)} not found "
            "(run scripts/generate_demo_data.py to write it); "
            "using the in-process ground truth instead."
        )
        return generated["media_specs"]  # type: ignore[return-value]

    with GROUND_TRUTH_PATH.open(encoding="utf-8") as fp:
        metadata = json.load(fp)

    expected = {
        "seed": SEED,
        "start_week": str(pd.Timestamp(df["week_start"].iloc[0]).date()),
        "end_week": str(pd.Timestamp(df["week_start"].iloc[-1]).date()),
    }
    mismatched = {key: (metadata.get(key), value) for key, value in expected.items() if metadata.get(key) != value}
    if mismatched:
        raise SystemExit(
            f"{GROUND_TRUTH_PATH} is stale against the current generator: {mismatched}. "
            "Regenerate it with `uv run python scripts/generate_demo_data.py`."
        )
    return metadata["media_specs"]


def recovery_table(
    recovered: dict[str, dict[str, float]],
    media_specs: dict[str, dict[str, float]],
    search_table: pd.DataFrame,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare recovered transform parameters against the generating values.

    ``validation_mape_spread`` is the range of the search objective across the whole
    grid for that channel, as a fraction of its best value. A tiny spread means the
    data cannot tell the candidates apart, so whatever the search picks is noise —
    which is the difference between "recovered the wrong value" and "had nothing to
    recover it from".
    """

    mape_by_channel = search_table.groupby("channel")["validation_mape"]
    mape_min = mape_by_channel.min()
    mape_max = mape_by_channel.max()

    rows = []
    for spend_column in spend_columns(df):
        channel_key = spend_column.removesuffix("_spend_gbp")
        label = CHANNEL_LABELS[spend_column]
        truth = media_specs[channel_key]
        fitted = recovered[spend_column]
        true_decay = float(truth["decay"])
        true_half_saturation = float(truth["half_saturation"])
        rows.append(
            {
                "channel": label,
                "true_decay": true_decay,
                "recovered_decay": float(fitted["adstock_decay"]),
                "decay_abs_error": abs(float(fitted["adstock_decay"]) - true_decay),
                "decay_grid_floor": min(abs(candidate - true_decay) for candidate in DECAY_CANDIDATES),
                "true_half_saturation_gbp": true_half_saturation,
                "recovered_half_saturation_gbp": float(fitted["half_saturation"]),
                "half_saturation_abs_pct_error": abs(
                    float(fitted["half_saturation"]) - true_half_saturation
                )
                / true_half_saturation,
                "half_saturation_grid_floor_pct": min(
                    abs(candidate - true_half_saturation) for candidate in HALF_SATURATION_CANDIDATES_GBP
                )
                / true_half_saturation,
                "best_validation_mape": float(mape_min[label]),
                "worst_validation_mape": float(mape_max[label]),
                "validation_mape_spread": float((mape_max[label] - mape_min[label]) / mape_min[label]),
            }
        )
    return pd.DataFrame(rows)


def parameter_sensitivity(
    df: pd.DataFrame,
    neutral: dict[str, dict[str, float]],
    searched: dict[str, dict[str, float]],
) -> pd.DataFrame:
    """Ask what handing the model the true transforms actually buys.

    The repo's default transform parameters are the generating ones, so every headline
    metric is conditional on knowing the answer in advance. This refits the same model
    under three parameter sets and reports what changes. It is the measured version of
    that caveat: if accuracy barely moves, the conditionality is not propping up the
    accuracy claims, and the sensitivity that *does* matter can be named precisely.
    """

    scenarios: list[tuple[str, dict[str, dict[str, float]] | None]] = [
        ("Generator truth (repo default)", None),
        ("Neutral (decay 0.35, half-sat GBP 100k)", neutral),
        ("Independent search result", searched),
    ]
    rows = []
    for label, parameters in scenarios:
        result = fit_mmm_foundation_model(df, holdout_weeks=HOLDOUT_WEEKS, media_parameters=parameters)
        roi = result.contribution_table["estimated_roi"]
        rows.append(
            {
                "scenario": label,
                "holdout_mape": result.metrics["test_mape"],
                "holdout_rmse_gbp": result.metrics["test_rmse_gbp"],
                "train_r_squared": result.metrics["train_r_squared"],
                "mean_estimated_roi": float(roi.mean()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    df, generated = generate_weekly_demo_data(seed=SEED)
    media_specs = load_ground_truth(df, generated)

    neutral_seed = {
        column: {
            "adstock_decay": NEUTRAL_DECAY,
            "half_saturation": NEUTRAL_HALF_SATURATION_GBP,
            "slope": SLOPE,
        }
        for column in spend_columns(df)
    }
    calibration = calibrate_mmm_parameters(
        df,
        holdout_weeks=HOLDOUT_WEEKS,
        validation_weeks=VALIDATION_WEEKS,
        decay_candidates=DECAY_CANDIDATES,
        half_saturation_candidates_gbp=HALF_SATURATION_CANDIDATES_GBP,
        initial_parameters=neutral_seed,
    )

    table = recovery_table(calibration.best_parameters, media_specs, calibration.search_table, df)
    sensitivity = parameter_sensitivity(df, neutral_seed, calibration.best_parameters)
    decay_hits = int((table["decay_abs_error"] <= table["decay_grid_floor"] + 1e-9).sum())
    half_saturation_hits = int(
        (table["half_saturation_abs_pct_error"] <= table["half_saturation_grid_floor_pct"] + 1e-9).sum()
    )

    summary = {
        "seed": SEED,
        "holdout_weeks": HOLDOUT_WEEKS,
        "validation_weeks": VALIDATION_WEEKS,
        "slope_assumed_not_recovered": SLOPE,
        "decay_candidates": list(DECAY_CANDIDATES),
        "half_saturation_candidates_gbp": list(HALF_SATURATION_CANDIDATES_GBP),
        "channels": int(len(table)),
        "decay_at_nearest_grid_point": decay_hits,
        "half_saturation_at_nearest_grid_point": half_saturation_hits,
        "mean_decay_abs_error": float(table["decay_abs_error"].mean()),
        "mean_half_saturation_abs_pct_error": float(table["half_saturation_abs_pct_error"].mean()),
        "grid_points_per_channel": int(len(DECAY_CANDIDATES) * len(HALF_SATURATION_CANDIDATES_GBP)),
        "validation_mape_min": float(calibration.search_table["validation_mape"].min()),
        "validation_mape_max": float(calibration.search_table["validation_mape"].max()),
        "max_validation_mape_spread": float(table["validation_mape_spread"].max()),
        "recovery_table": table.to_dict(orient="records"),
        "parameter_sensitivity": sensitivity.to_dict(orient="records"),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "transform_recovery_summary.json"
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print("=== Adstock and saturation recovery (independent grid, neutral seed) ===")
    print(table.to_string(index=False))
    print(f"\nDecay at nearest grid point: {decay_hits}/{len(table)} channels")
    print(f"Half-saturation at nearest grid point: {half_saturation_hits}/{len(table)} channels")
    print(f"Mean absolute decay error: {summary['mean_decay_abs_error']:.3f}")
    print(f"Mean absolute half-saturation error: {summary['mean_half_saturation_abs_pct_error']:.1%}")
    print(
        f"Validation MAPE across all {summary['grid_points_per_channel']} grid points per channel: "
        f"{summary['validation_mape_min']:.2%} to {summary['validation_mape_max']:.2%} "
        f"(worst per-channel spread {summary['max_validation_mape_spread']:.1%} of best)"
    )
    print("\n=== What does knowing the true transforms buy? ===")
    print(sensitivity.to_string(index=False))
    print(f"\nwrote {output_path}")


if __name__ == "__main__":
    main()
