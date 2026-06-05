# Phase 14: Bayesian MMM Foundations

## Objective

Add a Bayesian posterior layer to the active MMM workflow so the project can discuss posterior uncertainty, priors, and experiment-informed measurement in a more mature way.

## What Was Added

This phase adds a lightweight conjugate Bayesian regression over the existing MMM design matrix:

- Posterior coefficient draws for transformed media and control features.
- Channel contribution and ROI posterior intervals.
- Holdout posterior predictive intervals.
- Prior table showing whether each media prior is based on the MMM coefficient or experiment evidence.
- Diagnostics for holdout coverage, posterior MAPE, posterior sigma, and experiment-informed prior count.

## Experiment-Informed Priors

When approved lift-test evidence is available, the Bayesian layer nudges media coefficient priors using channel-level calibration factors.

This creates a practical bridge between:

- MMM response modeling.
- Incrementality evidence governance.
- Posterior uncertainty communication.

## Interpretation Guardrails

This is not yet a full Bayesian MMM engine.

It does not sample:

- Adstock decay parameters.
- Saturation parameters.
- Hierarchical geo-level effects.
- Long-term brand effects.
- Experiment likelihoods directly inside the model.

It is still valuable because it introduces Bayesian workflow concepts without hiding the assumptions. The dashboard can now show priors, posterior intervals, and predictive coverage in a way that is suitable for a portfolio project and a future production roadmap.

## Future Product Path

A stronger next version should use PyMC or NumPyro to model:

- Media coefficients with positivity constraints.
- Adstock and saturation parameters as posterior quantities.
- Experiment readouts as calibration likelihoods.
- Hierarchical variation by market, product group, or customer segment.
- Posterior predictive checks and convergence diagnostics.

## Phase 14 Done Criteria

Phase 14 is complete when:

- Bayesian posterior utilities exist in reusable package code.
- Experiment-informed priors can be generated from lift-test evidence.
- Contribution, ROI, and holdout prediction intervals are produced from posterior draws.
- Dashboard output shows Bayesian diagnostics and posterior tables.
- Tests cover outputs, reproducibility, prior behavior, and validation.
