# Roadmap

Marketing Effectiveness Lab is a **portfolio / reference implementation** for marketing
measurement. This roadmap is about deepening the *methodology* and *engineering* — not
building a commercial product. There is no proprietary application, pricing, or go-to-market
plan; those are explicit non-goals.

## Current state

A reusable Python package plus a Streamlit dashboard. It supports deterministic demo data
and real public datasets, documented CSV contracts, connector validation, MMM-style modeling
(adstock, saturation, contribution, ROI), uncertainty and a lightweight Bayesian layer,
experiment/lift-test calibration, profit-aware budget optimization, CRM experiment
workflows, and a local artifact registry — all covered by an automated test suite.

## Methodology directions

1. **Deeper Bayesian MMM** — move from the conjugate posterior over the fixed design matrix
   toward a sampler that also treats adstock and saturation parameters as random, with
   posterior predictive checks.
2. **Stronger calibration** — richer geo-lift / incrementality designs and a clearer
   reconciliation between experiment evidence and modeled contribution.
3. **Validation depth** — time-series cross-validation, backtesting across multiple holdout
   windows, and sensitivity analysis on priors and transformation parameters.
4. **Identifiability** — diagnostics for collinearity between channels and controls, and for
   how well spend variation identifies each response curve.

## Engineering directions

- Type checking and expanded test coverage on the modeling paths.
- Reproducibility: pinned environments, run manifests, and deterministic seeds (already
  partly in place via the artifact registry and manifests).
- Documentation of every modeling assumption alongside the code that implements it.

## Non-goals

- A proprietary or multi-tenant application, pricing, packaging, or go-to-market.
- Handling raw PII in the public demo.
- Claiming production approval or audit readiness.
- Replacing specialist MMM tools (Google Meridian, Meta Robyn, PyMC-Marketing) in
  high-stakes budget decisions.
- Presenting deterministic demo data as real brand performance.

## Principle

Useful measurement work is transparent about its assumptions, data limits, and where human
judgment remains necessary. This project optimizes for being **legible and inspectable**,
not for being a product.
