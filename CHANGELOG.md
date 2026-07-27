# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Post-archive correctness work. No new capability; two claims that could not fail were replaced
with measurements that can.

### Fixed

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
