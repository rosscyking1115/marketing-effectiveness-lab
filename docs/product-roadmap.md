# Roadmap

Marketing Effectiveness Lab is a reference implementation for marketing measurement. This roadmap
is about deepening the methodology and the engineering, not building a commercial product. There
is no proprietary application, pricing, or go-to-market plan, and those are explicit non-goals.

## Current state

A reusable Python package with a Streamlit dashboard. It runs on deterministic demo data and real
public datasets, with documented CSV contracts, connector validation, MMM-style modelling
(adstock, saturation, contribution, ROI), uncertainty and a lightweight Bayesian layer,
experiment and lift-test calibration, profit-aware budget optimisation, CRM experiment workflows,
and a local artifact registry. An automated test suite covers all of it.

## Methodology directions

1. A deeper Bayesian MMM: move from the conjugate posterior over the fixed design matrix towards a
   sampler that also treats adstock and saturation parameters as random, with posterior predictive
   checks.
2. Stronger calibration: richer geo-lift and incrementality designs, and a clearer reconciliation
   between experiment evidence and modelled contribution.
3. More validation: time-series cross-validation, backtesting across multiple holdout windows, and
   sensitivity analysis on priors and transformation parameters.
4. Identifiability: diagnostics for collinearity between channels and controls, and for how well
   spend variation identifies each response curve.

## Engineering directions

Type checking and wider test coverage on the modelling paths. Reproducibility through pinned
environments, run manifests, and deterministic seeds, some of which the artifact registry and
manifests already handle. Every modelling assumption documented alongside the code implementing
it.

## Non-goals

- A proprietary or multi-tenant application, pricing, packaging, or go-to-market.
- Handling raw PII in the public demo.
- Claiming production approval or audit readiness.
- Replacing specialist MMM tools (Google Meridian, Meta Robyn, PyMC-Marketing) in high-stakes
  budget decisions.
- Presenting deterministic demo data as real brand performance.

## Principle

Useful measurement work is transparent about its assumptions, its data limits, and where human
judgement is still doing the work. This project optimises for being legible and inspectable.
