# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-06

First tagged release of the reference implementation.

### Added

- **MMM engine**: geometric adstock, Hill saturation, OLS attribution with trend/seasonality/
  promotion/macro controls, contribution/ROI, and response curves (`mmm.py`).
- **Uncertainty**: frequentist coefficient Monte Carlo (`uncertainty.py`) and a conjugate
  Bayesian layer with experiment-informed priors (`bayesian.py`).
- **Incrementality calibration**: lift-test validation, evidence quality scoring, and
  MMM ↔ experiment reconciliation (`calibration.py`).
- **Budget optimisation**: marginal, constrained, profit-aware allocation (`budget.py`).
- **CRM analytics**: cohort/CLV/lapse-risk and target/holdout incrementality (`customer.py`).
- **Data pipeline**: connector contracts, weekly assembly, source diagnostics, and a
  deterministic demo generator; validated on the real public UCI Online Retail II dataset.
- **Governance & reporting**: readiness gates, run manifests, a local artifact registry, and an
  access-governance demo (RBAC + approval workflow + hash-chained audit log).
- **Validation studies** (reproducible scripts + docs): parameter recovery against known
  data-generating parameters, uncertainty calibration, MMM ↔ experiment reconciliation, and
  rolling-origin cross-validation.
- **Documentation**: methodology, validation, reconciliation, cross-validation, and a model card.

### Fixed

- Ill-conditioned Bayesian MMM posterior: the Normal-Inverse-Gamma sampler now whitens the design
  matrix before inversion, restoring calibrated interval coverage (previously collapsed to 0%).

### Changed

- Repositioned from a planned proprietary application to a neutral, Apache-2.0 **reference
  implementation**; documentation reframed to a methodology-first voice.

[0.1.0]: https://github.com/rosscyking1115/marketing-effectiveness-lab/releases/tag/v0.1.0
