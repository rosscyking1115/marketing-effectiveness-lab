# Case Study: Marketing Effectiveness Lab for UK Fashion Ecommerce

## Business Context

A UK fashion ecommerce retailer needs to understand how paid and owned marketing channels contribute to revenue, new-customer growth, and profit. The business invests across paid search, paid social, display, affiliates, email, influencers, organic demand, and promotions.

The commercial question is not only which channels correlate with revenue. The team needs a defensible workflow for estimating incremental contribution, understanding uncertainty, and comparing budget scenarios without ignoring seasonality, promotions, carryover, diminishing returns, and experiment evidence.

## Measurement Question

How should a fashion ecommerce brand allocate weekly marketing budget across channels to improve commercial outcomes while accounting for data quality, uncertainty, experiment calibration, and practical business constraints?

## Product Workflow

The lab is designed around the way marketing effectiveness work happens in practice:

1. Validate the weekly marketing schema and upstream connector exports.
2. Assemble ecommerce, GA4, paid media, CRM, affiliate, influencer, display, and control exports into a weekly MMM-ready dataset.
3. Diagnose source coverage, history length, outcome quality, and channel availability before modeling.
4. Explore revenue, spend, promotions, channel mix, correlations, and MMM readiness in an analyst dashboard.
5. Fit transparent baseline econometrics with a time-aware holdout.
6. Add MMM-style adstock, saturation, response curves, contribution, and ROI.
7. Quantify uncertainty with intervals and a lightweight Bayesian posterior layer.
8. Calibrate contribution estimates with governed lift-test evidence.
9. Compare profit-aware budget scenarios and constrained allocation recommendations.
10. Produce stakeholder-ready summaries and caveats.

## Current Outputs

The interactive dashboard provides:

- Revenue, order, new-customer, and media-spend KPIs
- Channel spend mix and promotion diagnostics
- MMM readiness checks and correlation scans
- Baseline econometric diagnostics with holdout performance
- MMM foundation diagnostics, response curves, contribution, and ROI
- Uncertainty intervals and Bayesian posterior diagnostics
- Lift-test upload, evidence quality review, and approved-only calibration
- Connector templates, weekly assembly, and source diagnostics
- Profit-aware scenario planning and constrained budget optimization
- Downloadable model-run report for review and lightweight audit trails
- Executive summary draft for stakeholder communication

## Technical Stack

- Python package code under `src/`
- Pandas and NumPy for data contracts, assembly, and analytics
- Statsmodels for transparent econometric baselines
- Plotly and Streamlit for the analyst-facing app
- Pytest and Ruff for automated quality checks
- uv for reproducible dependency management
- GitHub Actions, Streamlit Community Cloud, and GitHub Pages for deployment

## Modeling Notes

The project intentionally keeps the modeling transparent. The MMM foundation uses channel-specific adstock and saturation transformations, then fits a regression model with controls for trend, seasonality, promotion, organic demand, and macro placeholders.

The Bayesian layer adds posterior uncertainty over the active MMM design matrix and can use approved lift-test evidence as media priors. It is suitable for portfolio demonstration and directional planning, while the documentation clearly separates this from a full production Bayesian MMM sampler over all adstock and saturation parameters.

## Data Notes

The included dataset is generated from deterministic code for portfolio and development use. It is not ASOS data and does not copy any private brand data. The app can also validate uploaded weekly datasets or assemble connector exports that follow the documented contracts.

Uploaded files are parsed in memory in the current Streamlit version. A production version should add authentication, storage policy, audit logging, secrets management, and warehouse integrations before handling private company data.

## Portfolio Positioning

This project is aimed at roles such as:

- Marketing Data Scientist
- Commercial Data Scientist
- Product or Growth Analyst
- Retail Analytics Specialist
- Marketing Effectiveness Consultant
- Econometrics or Causal Inference Analyst
