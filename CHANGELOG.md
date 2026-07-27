# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Post-archive correctness work. No new capability; two claims that could not fail were replaced
with measurements that can.

### Fixed

- **The test suite could not tell the analytics apart from a constant.** An external sabotage
  sweep flagged it and the finding reproduced: freezing metric-bearing functions to
  shape-preserving constants left the suite green. Four functions were completely undetectable —
  `analytics.summarize_kpis`, `analytics.channel_summary`, `analytics.promotion_summary` and
  `uncertainty.simulate_mmm_uncertainty` each produced **zero** red tests — and only 20 of 139
  tests noticed a fully frozen model. The cause was assertions about shape, column names, row
  counts and `> 0` ranges, all satisfied by a constant. `test_dashboard_metrics_are_computed`
  promised computation in its name while asserting only that three numbers were positive, and
  `test_simulate_mmm_uncertainty_returns_intervals` asserted `lower <= upper`, equally true of a
  constant.

  Added `tests/test_metric_sensitivity.py`: 15 tests covering the derived dashboard columns, KPI
  totals, channel summary, promotion summary, Hill saturation, MMM features, MMM predictions,
  holdout error under a scrambled target, contribution and ROI, baseline econometrics, budget
  scenario, budget optimiser, and uncertainty intervals. Each is either an oracle that recomputes
  the metric independently or a sensitivity check that perturbs an input and requires the output to
  move, and **each was proven to fail under injection** before being committed.

  Added `scripts/sabotage_sweep.py` so the audit is repeatable rather than a one-off claim. It
  freezes one function at a time, reports per function, and exits non-zero if any function survives
  undetected. All 14 audited functions are now detected; per-function detection counts went 0 → 2
  (`summarize_kpis`), 0 → 1 (`channel_summary`), 0 → 1 (`promotion_summary`), 0 → 2
  (`simulate_mmm_uncertainty`) and 3 → 10 (`hill_saturation`).

  Note: `test_hill_saturation_is_bounded_and_monotonic` survives a frozen curve, because a constant
  array is trivially sorted and trivially within `[0, 1]`. It is kept, and the new
  `test_hill_saturation_responds_to_spend_and_half_saturation` is what actually holds the curve to
  its definition.

- `customer_future_value_backtest()` took each segment's expected future margin from the mean of
  the actual future margins it then scored against, making `mean_absolute_error_gbp` an in-sample
  dispersion rather than forecast error. Expectations are now estimated on a non-overlapping
  earlier fit window and scored out of sample, with a new `baseline_mean_absolute_error_gbp`
  column (pooled fit-window mean) to compare against. See
  [`docs/phase-26-empirical-clv-lapse-risk.md`](docs/phase-26-empirical-clv-lapse-risk.md).

### Added

- `scripts/validate_transform_recovery.py`: recovery study for the adstock and saturation
  parameters, which the existing recovery study assumes rather than tests. It searches an absolute
  grid from a neutral seed and scores against `data/demo/ground_truth_metadata.json` — written by
  the generator since day one and read by nothing until now — with a staleness guard and a
  fallback for fresh clones, where that directory is git-ignored. Result: the parameters are not
  recovered, because the validation objective is flat across the grid. Written up as section 3 of
  [`docs/validation.md`](docs/validation.md).
- `calibrate_mmm_parameters()` accepts `half_saturation_candidates_gbp` (an absolute grid) and
  `initial_parameters` (a neutral seed), so the search can be run without anchoring on
  `DEFAULT_MEDIA_PARAMETERS` — which on the demo data are the generating values.
- Transform-parameter sensitivity, in the same script and write-up: the model refit under the
  generator's truth, neutral parameters, and the independent search result. Knowing the true
  transforms turns out to buy no accuracy (holdout MAPE 4.98% under deliberately wrong parameters
  against 5.11% under the truth) and to be worth about 13% of the ROI estimate. The defaults are
  therefore left at the generating values and the conditionality is reported next to the figures.
- `py.typed` marker and a non-strict `[tool.mypy]` configuration scoped to `src/`, plus `mypy` in
  the dev dependency group. CI is unchanged and does not gate on it; the 36-error baseline, its
  single root cause, and the condition for adding the gate are recorded in
  [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Type annotations for the four helpers in `data/features.py`, the only annotation gaps in the
  package, and a corrected module docstring: a `Series` in gives a `Series` out, but an `Index` or
  NumPy array in gives a NumPy array out, which the previous wording denied.

## [0.1.0] - 2026-07-06

First tagged release of the reference implementation.

### Added

- MMM engine in `mmm.py`: geometric adstock, Hill saturation, OLS attribution with trend,
  seasonality, promotion and macro controls, contribution and ROI, and response curves.
- Uncertainty in two layers: frequentist coefficient Monte Carlo (`uncertainty.py`) and a
  conjugate Bayesian layer with experiment-informed priors (`bayesian.py`).
- Incrementality calibration in `calibration.py`: lift-test validation, evidence quality
  scoring, and reconciliation between MMM and experiments.
- Budget optimisation in `budget.py`: marginal, constrained, and profit-aware allocation.
- CRM analytics in `customer.py`: cohort, CLV and lapse-risk analysis, and target/holdout
  incrementality.
- Data pipeline: connector contracts, weekly assembly, source diagnostics, and a deterministic
  demo generator. Validated against the UCI Online Retail II public dataset.
- Governance and reporting: readiness gates, run manifests, a local artifact registry, and an
  access-governance demo covering RBAC, an approval workflow, and a hash-chained audit log.
- Validation studies, each with a reproducible script and a write-up: parameter recovery
  against known generating parameters, uncertainty calibration, MMM-to-experiment
  reconciliation, and rolling-origin cross-validation.
- Documentation: methodology, validation, reconciliation, cross-validation, and a model card.

### Fixed

- The Normal-Inverse-Gamma sampler built its posterior on an unwhitened design matrix, which
  was ill-conditioned enough to collapse interval coverage to zero. It now whitens the matrix
  before inversion, and coverage is restored.

### Changed

- Repositioned from a planned proprietary application to an Apache-2.0 reference
  implementation, and rewrote the documentation around the methodology.

[0.1.0]: https://github.com/rosscyking1115/marketing-effectiveness-lab/releases/tag/v0.1.0
