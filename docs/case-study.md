# Case study: marketing effectiveness for UK fashion ecommerce

## Business context

A UK fashion ecommerce retailer needs to understand how paid and owned marketing channels
contribute to revenue, new-customer growth, and profit. The business invests across paid search,
paid social, display, affiliates, email, influencers, organic demand, and promotions.

Knowing which channels correlate with revenue is the easy part. What the team needs is a
defensible workflow for estimating incremental contribution, understanding uncertainty, and
comparing budget scenarios while still accounting for seasonality, promotions, carryover,
diminishing returns, and experiment evidence.

## Measurement question

How should a fashion ecommerce brand allocate weekly marketing budget across channels to improve
commercial outcomes, given data quality, uncertainty, experiment calibration, and real business
constraints?

## Measurement workflow

The lab follows the order this work happens in practice:

1. Validate the weekly marketing schema and upstream connector exports.
2. Assemble ecommerce, GA4, paid media, CRM, affiliate, influencer, display, and control exports
   into a weekly MMM-ready dataset.
3. Diagnose source coverage, history length, outcome quality, and channel availability before
   modelling.
4. Explore revenue, spend, promotions, channel mix, correlations, and MMM readiness in an analyst
   dashboard.
5. Fit transparent baseline econometrics with a time-aware holdout.
6. Add MMM-style adstock, saturation, response curves, contribution, and ROI.
7. Quantify uncertainty with intervals and a lightweight Bayesian posterior layer.
8. Calibrate contribution estimates with governed lift-test evidence.
9. Compare profit-aware budget scenarios and constrained allocation recommendations.
10. Score recommendation readiness before stakeholder review.
11. Produce stakeholder-ready summaries and caveats.

## Current outputs

The interactive dashboard provides:

- Revenue, order, new-customer, and media-spend KPIs
- Channel spend mix and promotion diagnostics
- MMM readiness checks and correlation scans
- Baseline econometric diagnostics with holdout performance
- MMM foundation diagnostics, response curves, contribution, and ROI
- Uncertainty intervals and Bayesian posterior diagnostics
- Lift-test upload, evidence quality review, and approved-only calibration
- Connector templates, weekly assembly, and source diagnostics
- Profit-aware scenario planning and constrained budget optimisation
- Downloadable model-run report for review and lightweight audit trails
- Recommendation readiness scoring for model, evidence, profit, spend, and history checks
- Machine-readable run manifest for reproducible model-run review
- Executive summary draft for stakeholder communication

## Technical stack

Python package code under `src/`, with pandas and NumPy for data contracts, assembly and
analytics, and statsmodels for the econometric baselines. Plotly and Streamlit build the
analyst-facing app. Pytest and Ruff run the quality checks, uv manages dependencies, and GitHub
Actions, Streamlit Community Cloud, and GitHub Pages handle deployment.

## Modelling notes

The modelling is kept transparent on purpose. The MMM foundation applies channel-specific adstock
and saturation transformations, then fits a regression with controls for trend, seasonality,
promotion, organic demand, and macro placeholders.

The Bayesian layer adds posterior uncertainty over the active MMM design matrix, and can use
approved lift-test evidence as media priors. It suits workflow prototyping and directional
planning. It is not a full production Bayesian MMM sampler over all adstock and saturation
parameters, and the documentation keeps that line clear.

## Data notes

The included dataset is generated from deterministic code for development and public demo use. It
is not ASOS data and copies no private brand data. The app can also validate uploaded weekly
datasets, or assemble connector exports that follow the documented contracts.

Uploaded files are parsed in memory in the current Streamlit version. This is a reference
implementation rather than a hosted product, so anyone adapting it for private company data would
need authentication, a storage policy, audit logging, and secrets management first.

## Scope

This is a reference implementation, not a commercial product. What it shows is end-to-end
causal-measurement work: validating marketing and CRM data before modelling, comparing MMM,
lift-test and CRM experiment evidence, turning model output into budget and launch decisions
under uncertainty, and being explicit about assumptions, limitations, and where human judgement is
still needed.

[`methodology.md`](methodology.md) has the modelling detail: adstock, saturation, priors, holdout
and geo-lift calibration, and how each is validated.
