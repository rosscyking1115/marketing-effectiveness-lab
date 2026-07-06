"""Rolling-origin (expanding-window) cross-validation for the MMM.

A single train/test split reports one out-of-sample number; it can be lucky. Rolling-origin
backtesting refits the model on an expanding history and forecasts the next block repeatedly, so
the out-of-sample error is measured across several distinct periods. This is the honest way to
validate a time-series model and is the natural next step beyond the single 26-week holdout.

Each fold fits on ``df[:origin + horizon]`` with ``holdout_weeks = horizon``, so the model never
sees the block it is scored on, and the training window grows with each fold.

Writes one figure to ``docs/assets/validation/`` and a JSON summary. Regenerate with:

    uv run --group viz python scripts/rolling_origin_cv.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data  # noqa: E402
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "docs" / "assets" / "validation"

INK = "#1f2933"
MUTED = "#65717f"
GRID = "#e3e9ef"
GREEN = "#2f7d64"
BLUE = "#4b6f9c"
CORAL = "#c65f4b"

HORIZON = 13  # forecast one quarter ahead per fold
INITIAL_TRAIN = 91  # first fold trains on ~1.75 years before forecasting


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


def rolling_origin_cv(df: pd.DataFrame) -> pd.DataFrame:
    """Expanding-window backtest: refit and forecast the next HORIZON weeks per fold."""

    rows = []
    origin = INITIAL_TRAIN
    fold = 1
    while origin + HORIZON <= len(df):
        window = df.iloc[: origin + HORIZON]
        result = fit_mmm_foundation_model(window, holdout_weeks=HORIZON)
        test = result.test_frame
        rows.append(
            {
                "fold": fold,
                "train_weeks": origin,
                "forecast_start": str(pd.to_datetime(test["week_start"]).min().date()),
                "forecast_end": str(pd.to_datetime(test["week_start"]).max().date()),
                "test_mape": float(result.metrics["test_mape"]),
                "train_r_squared": float(result.metrics["train_r_squared"]),
            }
        )
        origin += HORIZON
        fold += 1
    return pd.DataFrame(rows)


def plot_folds(folds: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    mape_pct = folds["test_mape"] * 100
    bars = ax.bar(folds["fold"], mape_pct, color=BLUE, width=0.6)
    mean_mape = float(mape_pct.mean())
    ax.axhline(mean_mape, color=CORAL, linestyle="--", linewidth=1.4, label=f"Mean {mean_mape:.1f}%")
    for rect, label in zip(bars, folds["forecast_start"], strict=True):
        ax.text(
            rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{label}\n",
            ha="center", va="bottom", fontsize=7, color=MUTED,
        )
    _style_axes(ax)
    ax.set_title(
        "Rolling-origin cross-validation — out-of-sample MAPE per fold",
        fontsize=12, weight="bold",
    )
    ax.set_xlabel("Fold (expanding training window, 13-week forecast)")
    ax.set_ylabel("Out-of-sample MAPE (%)")
    ax.set_xticks(folds["fold"])
    ax.set_ylim(0, max(mape_pct.max() * 1.35, 12))
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.tight_layout()
    path = OUTPUT_DIR / "rolling-origin-cv.png"
    fig.savefig(path, dpi=120, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, _ = generate_weekly_demo_data(seed=42)
    folds = rolling_origin_cv(df)
    plot_folds(folds)

    mape = folds["test_mape"]
    summary = {
        "horizon_weeks": HORIZON,
        "initial_train_weeks": INITIAL_TRAIN,
        "folds": len(folds),
        "mean_test_mape": float(mape.mean()),
        "std_test_mape": float(mape.std(ddof=1)),
        "worst_test_mape": float(mape.max()),
        "best_test_mape": float(mape.min()),
        "fold_table": folds.to_dict(orient="records"),
    }
    with (OUTPUT_DIR / "rolling_origin_cv_summary.json").open("w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)
    print(f"wrote {OUTPUT_DIR / 'rolling_origin_cv_summary.json'}")

    pd.set_option("display.width", 200)
    print("\n=== Rolling-origin cross-validation ===")
    print(folds.to_string(index=False))
    print(
        f"\nOut-of-sample MAPE across {len(folds)} folds: "
        f"mean {mape.mean():.1%}, std {mape.std(ddof=1):.1%}, "
        f"range {mape.min():.1%}-{mape.max():.1%}"
    )


if __name__ == "__main__":
    main()
