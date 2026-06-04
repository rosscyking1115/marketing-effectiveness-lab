# Case Study: Marketing Effectiveness Lab for UK Fashion Ecommerce

## Business Context

A UK fashion ecommerce retailer wants to understand how paid and owned marketing channels contribute to revenue.

The business uses several acquisition and retention channels:

- Paid search
- Paid social
- Display
- Affiliates
- Email
- Influencer marketing
- Organic search
- Promotions

The commercial team wants to know which channels are driving incremental value, where diminishing returns may exist, and how budget could be reallocated.

## Core Question

How should a UK fashion ecommerce brand allocate weekly marketing budget across channels to improve revenue while accounting for seasonality, promotions, carryover, diminishing returns, and uncertainty?

## Approach

The project is built in phases:

1. Create a realistic weekly marketing dataset and validation schema.
2. Build an analyst dashboard for trends, channel mix, and MMM readiness.
3. Fit a baseline econometric model with time-aware holdout validation.
4. Add MMM-style adstock and saturation transformations.
5. Estimate directional channel contribution and ROI.
6. Build a budget scenario planner.
7. Generate executive-ready summary text and caveats.
8. Add uncertainty intervals and experiment calibration diagnostics.

## Current Outputs

The dashboard provides:

- Revenue and media spend trends
- Channel spend mix
- Promotion comparison
- MMM readiness checks
- Correlation scan
- Baseline econometric diagnostics
- MMM foundation diagnostics
- Estimated contribution and ROI
- Response curves
- Uncertainty intervals
- Incrementality calibration diagnostics
- Lift-test evidence upload and validation
- Evidence quality review and approved-only calibration
- Profit-aware budget scenario planning
- Budget scenario planning
- Executive summary draft

## Technical Stack

- Python
- Pandas and NumPy
- Statsmodels
- Plotly
- Streamlit
- Pytest
- uv

## Modeling Notes

The current MMM foundation model is deterministic. It uses channel-specific adstock and saturation parameters, then fits an OLS model on transformed media features and controls.

The project now includes parameter search, coefficient uncertainty simulation, demo lift-test calibration, real-data-ready lift-test CSV upload, evidence governance, and profit-aware scenario planning. This is useful for directional scenario planning, but it is not yet a full Bayesian MMM.

## Future Enhancements

High-value next steps:

- Calibrated parameter search for adstock and saturation
- Bayesian MMM with PyMC-Marketing or Meridian
- Experiment registry with approval workflow
- Profit-aware optimization
- Posterior credible intervals for contribution and ROI
- Profit-aware budget optimization
- Real data import templates
- Production API and user authentication

## Portfolio Positioning

This project is suitable for roles in:

- Marketing data science
- Commercial data science
- Product analytics
- Retail analytics
- Marketing effectiveness consulting
- Econometrics and causal inference
