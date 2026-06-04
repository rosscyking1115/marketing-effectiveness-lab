# Phase 8: Calibrated MMM Search

## Objective

Add a bounded parameter search for MMM adstock and saturation assumptions.

This phase bridges the gap between fixed deterministic MMM foundations and a future Bayesian MMM implementation.

## What Calibration Does

The calibrated search tunes media transformation parameters using a time-aware validation split.

For each channel, it searches over:

- Adstock decay
- Half-saturation level

The model keeps the Hill slope fixed for now to keep the search stable and interpretable.

## Splitting Strategy

The workflow uses three time-aware regions:

1. Training period for fitting candidate models.
2. Validation period for selecting channel transformation parameters.
3. Final holdout period for evaluating the selected model.

This avoids random splits, which are inappropriate for weekly time-series marketing data.

## Dashboard Outputs

The dashboard now includes an optional Calibrated MMM Search section.

When enabled, it shows:

- Fixed MMM vs calibrated MMM metrics
- Calibrated transformation parameters
- Best validation candidate by channel
- Option to use calibrated MMM in the budget scenario planner

## Interpretation Guardrails

Calibration improves parameter assumptions, but it still does not provide full uncertainty.

The model still does not include:

- Bayesian posterior intervals
- Experiment-calibrated priors
- Full parameter uncertainty
- Hierarchical geo or market effects
- Production-grade model governance

The calibrated model is useful for directional comparison and scenario exploration. Final budget recommendations should use uncertainty-aware MMM and experiment calibration where possible.

## Phase 8 Done Criteria

Phase 8 is complete when:

- MMM functions can accept custom media parameters.
- A bounded validation search can select parameters.
- Calibration outputs are tested.
- The dashboard compares fixed and calibrated MMM.
- The budget planner can optionally use calibrated response curves.

