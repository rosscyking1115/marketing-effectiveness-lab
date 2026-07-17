# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
