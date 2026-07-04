"""Render real analytical outputs to PNGs for the README (and the product site).

Fits the models on the deterministic demo data and renders four decision-relevant
figures to docs/assets/readme/:

1. MMM response curves (diminishing returns by channel)
2. Estimated channel contribution and ROI
3. Holdout fit with an uncertainty band
4. CRM incrementality with 95% intervals

These are genuine outputs of the package, not mock-ups. Regenerate with:

    uv run --group viz python scripts/generate_readme_assets.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from marketing_effectiveness_lab.customer import (  # noqa: E402
    crm_incrementality_summary,
    prepare_customer_tables,
)
from marketing_effectiveness_lab.data.customer_generator import generate_customer_demo_data  # noqa: E402
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data  # noqa: E402
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model  # noqa: E402
from marketing_effectiveness_lab.uncertainty import simulate_mmm_uncertainty  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "docs" / "assets" / "readme"

INK = "#1f2933"
MUTED = "#65717f"
GRID = "#e3e9ef"
GREEN = "#2f7d64"
BLUE = "#4b6f9c"
CORAL = "#c65f4b"
GOLD = "#9a7b3f"
PALETTE = [GREEN, BLUE, CORAL, GOLD, "#7a6f9b", "#3f8f9a"]


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


def response_curves(mmm) -> None:
    curves = mmm.response_curves
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for color, (channel, group) in zip(PALETTE, curves.groupby("channel"), strict=False):
        ax.plot(
            group["spend_gbp"] / 1000,
            group["estimated_weekly_contribution_gbp"] / 1000,
            label=channel,
            color=color,
            linewidth=2,
        )
    _style_axes(ax)
    ax.set_title("MMM response curves — diminishing returns by channel", fontsize=12, weight="bold")
    ax.set_xlabel("Weekly spend (GBP thousands)")
    ax.set_ylabel("Estimated weekly contribution (GBP thousands)")
    ax.legend(frameon=False, fontsize=8, ncol=2, labelcolor=INK)
    _save(fig, "mmm-response-curves.png")


def contribution(mmm) -> None:
    table = mmm.contribution_table.sort_values("estimated_contribution_gbp")
    fig, ax = plt.subplots(figsize=(8, 4.4))
    bars = ax.barh(table["channel"], table["estimated_contribution_gbp"] / 1_000_000, color=GREEN)
    for rect, roi in zip(bars, table["estimated_roi"], strict=True):
        ax.text(
            rect.get_width(),
            rect.get_y() + rect.get_height() / 2,
            f"  {roi:.1f}x ROI",
            va="center",
            ha="left",
            fontsize=8,
            color=MUTED,
        )
    _style_axes(ax)
    ax.grid(axis="y", visible=False)
    ax.set_title("Estimated channel contribution and ROI", fontsize=12, weight="bold")
    ax.set_xlabel("Estimated contribution (GBP millions)")
    ax.margins(x=0.18)
    _save(fig, "channel-contribution.png")


def holdout_uncertainty(mmm) -> None:
    intervals = simulate_mmm_uncertainty(mmm, draws=500, seed=42).prediction_intervals
    weeks = pd.to_datetime(intervals["week_start"])
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.fill_between(
        weeks,
        intervals["prediction_lower_gbp"] / 1_000_000,
        intervals["prediction_upper_gbp"] / 1_000_000,
        color=BLUE,
        alpha=0.18,
        label="90% prediction interval",
    )
    ax.plot(weeks, intervals["revenue_gbp"] / 1_000_000, color=INK, linewidth=2, label="Actual revenue")
    ax.plot(
        weeks,
        intervals["prediction_mean_gbp"] / 1_000_000,
        color=BLUE,
        linewidth=2,
        linestyle="--",
        label="Predicted mean",
    )
    _style_axes(ax)
    ax.set_title("Holdout fit with uncertainty band", fontsize=12, weight="bold")
    ax.set_xlabel("Holdout week")
    ax.set_ylabel("Weekly revenue (GBP millions)")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.autofmt_xdate()
    _save(fig, "holdout-uncertainty.png")


def crm_incrementality() -> None:
    tables = prepare_customer_tables(generate_customer_demo_data(seed=42).as_tables())
    summary = crm_incrementality_summary(tables["crm_campaigns"], tables["crm_events"])
    summary = summary.sort_values("conversion_lift")
    lift = summary["conversion_lift"] * 100
    lower = (summary["conversion_lift"] - summary["conversion_lift_lower"]) * 100
    upper = (summary["conversion_lift_upper"] - summary["conversion_lift"]) * 100

    fig, ax = plt.subplots(figsize=(8, 4.4))
    y = range(len(summary))
    colors = [GREEN if value > 0 else CORAL for value in summary["conversion_lift"]]
    ax.errorbar(
        lift, list(y), xerr=[lower, upper], fmt="none", ecolor=MUTED, elinewidth=1.2, capsize=3
    )
    ax.scatter(lift, list(y), color=colors, s=45, zorder=3)
    ax.axvline(0, color=MUTED, linewidth=1, linestyle=":")
    ax.set_yticks(list(y))
    ax.set_yticklabels(summary["campaign_name"], fontsize=8)
    _style_axes(ax)
    ax.grid(axis="y", visible=False)
    ax.set_title("CRM incrementality — conversion lift with 95% intervals", fontsize=12, weight="bold")
    ax.set_xlabel("Conversion lift (percentage points)")
    _save(fig, "crm-incrementality.png")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, _ = generate_weekly_demo_data(seed=42)
    mmm = fit_mmm_foundation_model(df, holdout_weeks=26)

    response_curves(mmm)
    contribution(mmm)
    holdout_uncertainty(mmm)
    crm_incrementality()
    print(f"Assets written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
