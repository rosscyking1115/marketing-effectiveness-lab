"""Validation study: parameter recovery and uncertainty calibration.

Because the demo dataset is *generated* from known adstock, saturation, and effect
parameters (see ``data/generator.py``), we can ask two questions that most portfolio
MMM projects cannot answer on real data:

1. **Parameter recovery** — does the fitted MMM recover the true channel effects and ROI
   that generated the data?
2. **Uncertainty calibration** — do the Bayesian posterior-predictive intervals cover the
   held-out weeks at their nominal rate (e.g. does a 90% interval contain ~90% of holdout
   points)?

The generator uses the same geometric adstock and Hill saturation (slope 1.35) as the model,
and its per-channel ``decay`` / ``half_saturation`` match the model defaults, so the fitted
coefficient on ``{channel}_mmm`` is directly comparable to the true ``effect``.

Writes two figures to ``docs/assets/validation/`` and a JSON summary. Regenerate with:

    uv run --group viz python scripts/validate_recovery.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS, spend_columns  # noqa: E402
from marketing_effectiveness_lab.bayesian import fit_bayesian_mmm  # noqa: E402
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
PALETTE = [GREEN, BLUE, CORAL, GOLD, "#7a6f9b", "#3f8f9a"]

HOLDOUT_WEEKS = 26
SLOPE = 1.35
NOMINAL_LEVELS = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95)
DRAWS = 1200


def _style_axes(ax) -> None:
    ax.set_facecolor("white")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.label.set_color(MUTED)
    ax.xaxis.label.set_color(MUTED)
    ax.title.set_color(INK)
    ax.grid(True, color=GRID, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)


def _save(fig, name: str) -> None:
    fig.tight_layout()
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=120, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def true_channel_truth(df: pd.DataFrame, media_specs: dict) -> pd.DataFrame:
    """Compute the true per-channel contribution and ROI that generated the data."""

    rows = []
    for spend_column in spend_columns(df):
        channel_key = spend_column.removesuffix("_spend_gbp")
        specs = media_specs[channel_key]
        spend = df[spend_column].to_numpy(dtype=float)
        adstocked = geometric_adstock(spend, specs["decay"])
        saturated = hill_saturation(adstocked, specs["half_saturation"], SLOPE)
        contribution = saturated * specs["effect"]
        total_spend = float(spend.sum())
        rows.append(
            {
                "channel": CHANNEL_LABELS[spend_column],
                "feature": f"{spend_column}_mmm",
                "true_effect": float(specs["effect"]),
                "true_contribution_gbp": float(contribution.sum()),
                "true_roi": float(contribution.sum() / total_spend) if total_spend else 0.0,
            }
        )
    return pd.DataFrame(rows)


def parameter_recovery(bayes, truth: pd.DataFrame) -> pd.DataFrame:
    """Join true channel parameters to recovered posterior coefficients and ROI."""

    coef = bayes.coefficient_summary.set_index("feature")
    roi = bayes.contribution_intervals.set_index("channel")

    rows = []
    for _, row in truth.iterrows():
        feature = row["feature"]
        channel = row["channel"]
        c = coef.loc[feature]
        r = roi.loc[channel]
        effect_covered = bool(c["posterior_lower"] <= row["true_effect"] <= c["posterior_upper"])
        roi_covered = bool(r["roi_lower"] <= row["true_roi"] <= r["roi_upper"])
        rows.append(
            {
                "channel": channel,
                "true_effect": row["true_effect"],
                "recovered_effect": float(c["posterior_mean"]),
                "effect_lower": float(c["posterior_lower"]),
                "effect_upper": float(c["posterior_upper"]),
                "effect_covered": effect_covered,
                "true_roi": row["true_roi"],
                "recovered_roi": float(r["roi_mean"]),
                "roi_lower": float(r["roi_lower"]),
                "roi_upper": float(r["roi_upper"]),
                "roi_covered": roi_covered,
            }
        )
    return pd.DataFrame(rows)


def coverage_curve(mmm) -> pd.DataFrame:
    """Empirical holdout coverage of posterior-predictive intervals at each nominal level."""

    rows = []
    for level in NOMINAL_LEVELS:
        result = fit_bayesian_mmm(mmm, draws=DRAWS, seed=42, interval_width=level)
        rows.append(
            {
                "nominal": level,
                "empirical_coverage": float(result.diagnostics["holdout_coverage"]),
                "holdout_mape": float(result.diagnostics["holdout_mape"]),
            }
        )
    return pd.DataFrame(rows)


def plot_roi_recovery(recovery: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    lo = (recovery["recovered_roi"] - recovery["roi_lower"]).clip(lower=0)
    hi = (recovery["roi_upper"] - recovery["recovered_roi"]).clip(lower=0)
    ax.errorbar(
        recovery["true_roi"],
        recovery["recovered_roi"],
        yerr=[lo, hi],
        fmt="none",
        ecolor=MUTED,
        elinewidth=1.3,
        capsize=3,
        zorder=2,
    )
    ax.scatter(recovery["true_roi"], recovery["recovered_roi"], color=GREEN, s=55, zorder=3)
    for _, row in recovery.iterrows():
        ax.annotate(
            f"  {row['channel']}",
            (row["true_roi"], row["recovered_roi"]),
            fontsize=8,
            color=INK,
            va="center",
        )
    limit = float(max(recovery["true_roi"].max(), recovery["roi_upper"].max()) * 1.12)
    ax.plot([0, limit], [0, limit], color=CORAL, linewidth=1.2, linestyle="--", label="Perfect recovery (y = x)")
    ax.set_xlim(0, limit)
    ax.set_ylim(0, limit)
    _style_axes(ax)
    ax.set_title("Parameter recovery — true vs recovered channel ROI", fontsize=12, weight="bold")
    ax.set_xlabel("True ROI (data-generating)")
    ax.set_ylabel("Recovered ROI (posterior mean, 90% interval)")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="upper left")
    _save(fig, "parameter-recovery-roi.png")


def plot_coverage(curve: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    ax.plot([0, 1], [0, 1], color=CORAL, linewidth=1.2, linestyle="--", label="Perfect calibration (y = x)")
    ax.plot(
        curve["nominal"],
        curve["empirical_coverage"],
        color=BLUE,
        linewidth=2,
        marker="o",
        markersize=6,
        label="Posterior-predictive intervals",
    )
    ax.set_xlim(0.45, 1.0)
    ax.set_ylim(0.45, 1.02)
    _style_axes(ax)
    ax.set_title("Uncertainty calibration — nominal vs empirical holdout coverage", fontsize=12, weight="bold")
    ax.set_xlabel("Nominal interval level")
    ax.set_ylabel("Empirical holdout coverage")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="upper left")
    _save(fig, "calibration-coverage.png")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, ground_truth = generate_weekly_demo_data(seed=42)
    media_specs = ground_truth["media_specs"]

    mmm = fit_mmm_foundation_model(df, holdout_weeks=HOLDOUT_WEEKS)
    bayes = fit_bayesian_mmm(mmm, draws=DRAWS, seed=42, interval_width=0.90)

    truth = true_channel_truth(df, media_specs)
    recovery = parameter_recovery(bayes, truth)
    curve = coverage_curve(mmm)

    plot_roi_recovery(recovery)
    plot_coverage(curve)

    coverage_at_90 = float(curve.loc[curve["nominal"] == 0.90, "empirical_coverage"].iloc[0])
    summary = {
        "holdout_weeks": HOLDOUT_WEEKS,
        "posterior_draws": DRAWS,
        "coverage_at_90pct": coverage_at_90,
        "roi_within_90pct_interval": int(recovery["roi_covered"].sum()),
        "effect_within_90pct_interval": int(recovery["effect_covered"].sum()),
        "channels": len(recovery),
        "mean_abs_roi_error": float((recovery["recovered_roi"] - recovery["true_roi"]).abs().mean()),
        "coverage_curve": curve.to_dict(orient="records"),
        "recovery_table": recovery.to_dict(orient="records"),
    }
    with (OUTPUT_DIR / "validation_summary.json").open("w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)
    print(f"wrote {OUTPUT_DIR / 'validation_summary.json'}")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print("\n=== Parameter recovery ===")
    print(
        recovery[
            [
                "channel",
                "true_effect",
                "recovered_effect",
                "effect_covered",
                "true_roi",
                "recovered_roi",
                "roi_lower",
                "roi_upper",
                "roi_covered",
            ]
        ].to_string(index=False)
    )
    print("\n=== Coverage curve ===")
    print(curve.to_string(index=False))
    print(f"\nCoverage at nominal 90%: {coverage_at_90:.1%}")
    print(f"True ROI inside 90% interval: {summary['roi_within_90pct_interval']}/{summary['channels']} channels")
    print(f"True effect inside 90% interval: {summary['effect_within_90pct_interval']}/{summary['channels']} channels")


if __name__ == "__main__":
    main()
