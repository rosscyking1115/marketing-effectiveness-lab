"""MMM <-> experiment reconciliation: the core causal-measurement loop.

The [validation study](../docs/validation.md) showed the observational MMM inflates channel
ROI ~2-3x because media spend is confounded with seasonal demand. This script closes the loop:
a clean incrementality experiment measures the *true* lift, and the calibration layer reconciles
the biased MMM estimate toward it.

"MMM says X, the geo-lift says Y, here is the reconciled estimate."

Because the demo data is generated from known parameters, we can simulate an *honest* geo-lift:
each experiment measures the true incremental revenue the generating process produced over the
experiment window (plus realistic measurement noise). We then apply the engine's calibration to
the observational MMM and compare all three: true ROI, observational MMM ROI, and
experiment-calibrated ROI.

Writes one figure to ``docs/assets/validation/`` and a JSON summary. Regenerate with:

    uv run --group viz python scripts/reconcile_mmm_experiments.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS, spend_columns  # noqa: E402
from marketing_effectiveness_lab.calibration import apply_lift_calibration  # noqa: E402
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data  # noqa: E402
from marketing_effectiveness_lab.mmm import (  # noqa: E402
    fit_mmm_foundation_model,
    geometric_adstock,
    hill_saturation,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "docs" / "assets" / "validation"

INK = "#1f2933"
MUTED = "#65717f"
GRID = "#e3e9ef"
GREEN = "#2f7d64"
BLUE = "#4b6f9c"
CORAL = "#c65f4b"
GOLD = "#9a7b3f"

HOLDOUT_WEEKS = 26
SLOPE = 1.35
EXPERIMENT_WEEKS = 8
# Channels a team would realistically run paid-media geo-lift / conversion-lift tests on.
EXPERIMENT_CHANNELS = {"Paid search", "Paid social", "Display", "Influencer"}
EXPERIMENT_TYPES = {
    "Paid search": "Geo holdout",
    "Paid social": "Conversion lift",
    "Display": "Matched-market test",
    "Influencer": "Brand-search lift",
}
MEASUREMENT_INTERVAL_PCT = 0.15  # +/- band a well-run experiment reports around its point estimate
RNG = np.random.default_rng(7)


def _style_axes(ax) -> None:
    ax.set_facecolor("white")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.title.set_color(INK)
    ax.grid(True, color=GRID, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)


def true_weekly_contribution(df: pd.DataFrame, media_specs: dict) -> dict[str, np.ndarray]:
    """Per-channel true weekly incremental revenue from the generating process."""

    contributions = {}
    for spend_column in spend_columns(df):
        specs = media_specs[spend_column.removesuffix("_spend_gbp")]
        adstocked = geometric_adstock(df[spend_column].to_numpy(dtype=float), specs["decay"])
        saturated = hill_saturation(adstocked, specs["half_saturation"], SLOPE)
        contributions[CHANNEL_LABELS[spend_column]] = saturated * specs["effect"]
    return contributions


def simulate_lift_tests(mmm, true_weekly: dict[str, np.ndarray]) -> pd.DataFrame:
    """Simulate honest geo-lift readouts: observed lift = true lift over the window + noise."""

    contribution = mmm.contribution_table.set_index("channel")
    rows = []
    for channel in EXPERIMENT_CHANNELS:
        model_lift = float(contribution.loc[channel, "avg_weekly_contribution_gbp"]) * EXPERIMENT_WEEKS
        true_lift = float(np.mean(true_weekly[channel])) * EXPERIMENT_WEEKS
        # A well-run experiment recovers the true lift up to modest measurement error.
        observed_lift = max(true_lift * float(RNG.normal(1.0, 0.05)), 1.0)
        interval = observed_lift * MEASUREMENT_INTERVAL_PCT
        rows.append(
            {
                "test_name": f"{channel} incrementality test",
                "channel": channel,
                "experiment_type": EXPERIMENT_TYPES[channel],
                "weeks": EXPERIMENT_WEEKS,
                "model_lift_gbp": max(model_lift, 1.0),
                "observed_lift_gbp": observed_lift,
                "observed_lift_lower_gbp": max(observed_lift - interval, 0.0),
                "observed_lift_upper_gbp": observed_lift + interval,
                "approval_status": "Approved",
            }
        )
    return pd.DataFrame(rows)


def reconcile(df: pd.DataFrame, media_specs: dict):
    mmm = fit_mmm_foundation_model(df, holdout_weeks=HOLDOUT_WEEKS)
    true_weekly = true_weekly_contribution(df, media_specs)
    lift_tests = simulate_lift_tests(mmm, true_weekly)
    calibrated = apply_lift_calibration(mmm.contribution_table, lift_tests)

    calibrated = calibrated.set_index("channel")
    rows = []
    for spend_column in spend_columns(df):
        channel = CHANNEL_LABELS[spend_column]
        spend = float(df[spend_column].sum())
        true_roi = float(np.sum(true_weekly[channel]) / spend) if spend else 0.0
        rows.append(
            {
                "channel": channel,
                "true_roi": true_roi,
                "mmm_roi": float(calibrated.loc[channel, "estimated_roi"]),
                "calibrated_roi": float(calibrated.loc[channel, "estimated_roi_calibrated"]),
                "calibration_status": str(calibrated.loc[channel, "calibration_status"]),
                "calibration_factor": float(calibrated.loc[channel, "calibration_factor"]),
            }
        )
    return pd.DataFrame(rows)


def plot_reconciliation(table: pd.DataFrame) -> None:
    experiment = table[table["calibration_status"] == "Experiment-calibrated"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    y = np.arange(len(experiment))
    height = 0.26
    ax.barh(y + height, experiment["mmm_roi"], height, color=CORAL, label="Observational MMM (biased)")
    ax.barh(y, experiment["calibrated_roi"], height, color=BLUE, label="Experiment-calibrated")
    ax.scatter(
        experiment["true_roi"], y + height / 2, color=INK, s=60, zorder=5, marker="D",
        label="True ROI (data-generating)",
    )
    ax.set_yticks(y + height / 2)
    ax.set_yticklabels(experiment["channel"])
    _style_axes(ax)
    ax.grid(axis="y", visible=False)
    ax.set_title(
        "MMM <-> experiment reconciliation — calibration corrects the bias",
        fontsize=12, weight="bold",
    )
    ax.set_xlabel("Return on ad spend (ROI)")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="lower right")
    fig.tight_layout()
    path = OUTPUT_DIR / "mmm-experiment-reconciliation.png"
    fig.savefig(path, dpi=120, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, ground_truth = generate_weekly_demo_data(seed=42)
    table = reconcile(df, ground_truth["media_specs"])
    plot_reconciliation(table)

    experiment = table[table["calibration_status"] == "Experiment-calibrated"]
    mmm_gap = float((experiment["mmm_roi"] - experiment["true_roi"]).abs().mean())
    cal_gap = float((experiment["calibrated_roi"] - experiment["true_roi"]).abs().mean())
    summary = {
        "experiment_weeks": EXPERIMENT_WEEKS,
        "mean_abs_roi_error_observational": mmm_gap,
        "mean_abs_roi_error_calibrated": cal_gap,
        "bias_reduction_pct": (1 - cal_gap / mmm_gap) * 100 if mmm_gap else 0.0,
        "table": table.to_dict(orient="records"),
    }
    with (OUTPUT_DIR / "reconciliation_summary.json").open("w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)
    print(f"wrote {OUTPUT_DIR / 'reconciliation_summary.json'}")

    pd.set_option("display.width", 200)
    print("\n=== MMM <-> experiment reconciliation ===")
    print(table.to_string(index=False))
    print(
        f"\nMean |ROI - true| : observational {mmm_gap:.2f}x  ->  calibrated {cal_gap:.2f}x "
        f"({summary['bias_reduction_pct']:.0f}% closer to truth)"
    )


if __name__ == "__main__":
    main()
