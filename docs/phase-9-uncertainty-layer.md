# Phase 9: MMM Uncertainty Layer

## Objective

Make model uncertainty visible in the Marketing Effectiveness Lab before moving to a full Bayesian MMM engine.

This phase adds coefficient simulation around the active MMM model to estimate:

- Channel contribution intervals
- Channel ROI intervals
- Holdout prediction intervals

## What This Layer Does

The uncertainty layer samples model coefficients from the fitted covariance matrix of the active MMM model.

It then converts those coefficient draws into:

- Simulated channel contribution totals
- Simulated ROI ranges
- Simulated holdout revenue predictions

The dashboard can run this on either:

- Fixed MMM foundations
- Calibrated MMM, when enabled

## Why This Matters

Marketing effectiveness tools are dangerous when they only show point estimates.

This phase lets the analyst see whether an estimated contribution is stable or uncertain before using it in scenario planning.

## Interpretation Guardrails

These intervals are not Bayesian posterior credible intervals.

They do not yet include:

- Uncertainty in adstock parameters
- Uncertainty in saturation parameters
- Experiment-calibrated priors
- Geo-level variation
- Full posterior diagnostics

They are still useful as a practical bridge toward Bayesian MMM because they force the product to communicate uncertainty rather than pretending single estimates are exact.

## Dashboard Outputs

The dashboard now includes:

- Contribution intervals by channel
- ROI intervals by channel
- Holdout prediction interval chart
- Adjustable simulation draw count

## Phase 9 Done Criteria

Phase 9 is complete when:

- MMM coefficient uncertainty can be simulated.
- Contribution and ROI intervals are generated.
- Holdout prediction intervals are generated.
- Tests cover interval outputs and input validation.
- The dashboard renders uncertainty charts and tables.

