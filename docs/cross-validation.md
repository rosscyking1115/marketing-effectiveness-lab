# Rolling-origin cross-validation

A single train/test split reports one out-of-sample number, and one number can be lucky — a
holdout that happens to land on an easy stretch of history flatters the model. **Rolling-origin
(expanding-window) backtesting** refits the model on a growing history and forecasts the next
block repeatedly, so generalization is measured across several distinct periods.

Reproduce with:

```powershell
uv run --group viz python scripts/rolling_origin_cv.py
```

## Setup

Each fold fits on `df[:origin + horizon]` with `holdout_weeks = horizon`, so the model is scored
only on weeks it never saw, and the training window expands fold to fold. Horizon is **13 weeks**
(one quarter ahead); the first fold trains on ~1.75 years.

![Rolling-origin cross-validation](assets/validation/rolling-origin-cv.png)

| Fold | Train weeks | Forecast window | Out-of-sample MAPE |
| --- | --- | --- | --- |
| 1 | 91 | 2024-09-30 → 2024-12-23 | 5.3% |
| 2 | 104 | 2024-12-30 → 2025-03-24 | 3.3% |
| 3 | 117 | 2025-03-31 → 2025-06-23 | 3.3% |
| 4 | 130 | 2025-06-30 → 2025-09-22 | 4.9% |
| 5 | 143 | 2025-09-29 → 2025-12-22 | 4.6% |

**Out-of-sample MAPE across 5 folds: mean 4.3%, std 0.9%, range 3.3%–5.3%.**

The error is stable across quarters — including fold 1, which forecasts the Black-Friday /
Q4 peak, the hardest period to predict. The single 26-week holdout (~5% MAPE) was not a lucky
draw; the model's accuracy holds up under repeated, honest backtesting.

## Honest benchmark context

This engine is a **transparent reference implementation**, deliberately kept legible, not a
competitor to the mature open-source MMM tools. How it relates to them:

| Tool | What it adds over this reference |
| --- | --- |
| **[Google Meridian](https://github.com/google/meridian)** | Hierarchical Bayesian MMM, full posterior over adstock/saturation, geo-level modeling, reach/frequency, built-in ROI priors from experiments. |
| **[Meta Robyn](https://github.com/facebookexperimental/Robyn)** | Ridge regression with evolutionary (Nevergrad) hyperparameter search over adstock/saturation, Pareto-front model selection, automated calibration to experiments. |
| **[PyMC-Marketing](https://github.com/pymc-labs/pymc-marketing)** | Full PyMC Bayesian MMM — MCMC (NUTS) over all transform parameters, custom priors, posterior predictive checks, time-varying effects. |

What this project does that a reviewer can see at a glance: every transformation, prior, and
validation step is documented next to the code that implements it
([`methodology.md`](methodology.md)), the estimator is checked against **known ground truth**
([`validation.md`](validation.md)), and the MMM↔experiment loop is demonstrated end to end
([`reconciliation.md`](reconciliation.md)). The tools above are what you would reach for in
production; this repository is where you would go to *understand how the pieces work*.

The clearest methodological gap versus those tools — sampling the adstock/saturation parameters
rather than fixing them, and modeling at the geo level — is the top item on the
[roadmap](product-roadmap.md).
