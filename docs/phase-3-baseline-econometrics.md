# Phase 3: Baseline Econometrics

## Objective

Create the first formal modeling benchmark before moving into full marketing mix modeling.

This phase fits a transparent OLS-style econometric model that predicts weekly revenue using:

- Log media spend by channel
- Promotion depth and promotion flags
- Holiday flags
- Seasonal collection flags
- Organic search demand
- Consumer confidence
- Inflation
- Trend and trend squared

## Why This Comes Before Bayesian MMM

A baseline model gives the project a useful diagnostic checkpoint:

- Can the available features explain revenue movement at all?
- Does the model generalize to recent holdout weeks?
- Are media variables directionally plausible?
- Are any features highly collinear?
- Which controls appear important before adding adstock and saturation?

This is not the final measurement model. It is a transparent benchmark that helps us reason about the data before adding more complex MMM machinery.

## Modeling Design

The model uses log revenue as the target and holds out the latest 26 weeks for time-aware evaluation.

The holdout is intentionally the most recent period. Random splits are not appropriate for this time-series setting because they can leak future patterns into training.

## Dashboard Outputs

The Streamlit dashboard now includes:

- Training R-squared
- Adjusted R-squared
- Training MAPE
- Holdout MAPE
- Holdout RMSE
- Actual vs predicted revenue chart
- Coefficient review table
- VIF collinearity table

## Interpretation Guardrails

Do not treat this baseline as a budget allocator.

The model does not yet include:

- Adstock
- Saturation
- Bayesian uncertainty
- Channel contribution decomposition
- Experiment calibration
- Incrementality priors
- Constrained budget optimization

Those are planned for the MMM phase.

## Phase 3 Done Criteria

Phase 3 is complete when:

- Baseline model code is reusable outside the dashboard.
- Tests cover model-frame creation and diagnostics.
- The dashboard shows model fit and holdout diagnostics.
- The documentation clearly distinguishes baseline econometrics from MMM.

