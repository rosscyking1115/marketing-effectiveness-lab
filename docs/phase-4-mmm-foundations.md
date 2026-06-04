# Phase 4: MMM Foundations

## Objective

Add the first marketing mix modeling mechanics before moving into full Bayesian MMM.

This phase introduces:

- Geometric adstock
- Hill-style saturation
- Channel-specific media transformations
- MMM-style revenue prediction
- Estimated channel contribution
- Estimated media ROI
- Response curves

## Why This Phase Exists

The project already has a transparent baseline econometric model. That model is useful, but it treats logged media spend as an ordinary feature.

MMM needs additional marketing-specific structure:

- Media impact can carry over into later weeks.
- More spend does not create unlimited incremental revenue.
- Channels can have different response shapes.
- Contribution and ROI should be separated from raw correlation.

This phase adds those mechanics in a deterministic, explainable way.

## Current Modeling Approach

The current MMM foundation model:

1. Applies geometric adstock to each paid media channel.
2. Applies Hill-style saturation to the adstocked media signal.
3. Fits an OLS model on revenue using transformed media features and business controls.
4. Holds out the latest 26 weeks for time-aware validation.
5. Estimates channel contribution as transformed media signal multiplied by its fitted coefficient.

## Current Media Parameters

The transformation parameters are fixed, channel-specific assumptions:

- Paid search: lower carryover, moderate saturation
- Paid social: medium carryover
- Display: higher carryover
- Affiliates: lower carryover
- Email: short carryover, lower saturation threshold
- Influencer: higher carryover

These values are sensible defaults for the synthetic business scenario. They are not yet estimated from data.

## Dashboard Outputs

The dashboard now includes:

- MMM train R-squared
- MMM adjusted R-squared
- MMM train MAPE
- MMM holdout MAPE
- MMM holdout RMSE
- Actual vs MMM foundation prediction
- Estimated media contribution by channel
- Estimated ROI by channel
- Estimated response curves
- Media transformation parameter table

## Interpretation Guardrails

The current MMM outputs are directional estimates, not final budget recommendations.

The model does not yet include:

- Bayesian uncertainty
- Prior calibration
- Experiment calibration
- Parameter search
- Posterior diagnostics
- Credible intervals
- Budget optimization constraints

The next modeling phase should improve parameter estimation and uncertainty.

## Phase 4 Done Criteria

Phase 4 is complete when:

- Adstock and saturation functions are implemented.
- MMM transformed media features are created.
- A deterministic MMM-style model can be fit.
- Contribution and response-curve outputs are available.
- The dashboard shows MMM foundations clearly.
- Tests cover transformations, model outputs, and sanity checks.

