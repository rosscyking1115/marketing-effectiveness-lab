# Phase 2: Analyst Dashboard

## Objective

Build the first usable analyst-facing experience for the Marketing Effectiveness Lab.

The Phase 2 dashboard is not yet a budget optimization tool. It is a diagnostic workspace for understanding the data before modeling:

- Revenue and media spend trends
- Channel spend mix
- Promotion and holiday behavior
- Channel-level spend summary
- Early MMM readiness checks
- Correlation diagnostics

## App

Run the dashboard with:

```powershell
uv run streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
```

The app loads `data/demo/fashion_retail_weekly.csv`. If the file is missing, it generates the demo dataset automatically.

## Analyst Workflow

1. Select a weekly date range.
2. Review revenue, media spend, blended ROAS, orders, and new customers.
3. Compare revenue and media spend trends.
4. Inspect spend mix across paid search, paid social, display, affiliates, email, and influencer.
5. Compare promotion and non-promotion weeks.
6. Review MMM readiness checks before moving into econometric modeling.
7. Use the correlation scan to identify potential multicollinearity and control-variable issues.

## Why This Comes Before MMM

MMM is not a push-button exercise. The analyst needs to understand whether the data has enough history, enough channel variation, visible promo effects, and reasonable control variables.

This phase gives the project a practical analytics workflow before adding heavier modeling.

## Phase 2 Done Criteria

Phase 2 is complete when:

- The dashboard runs locally.
- The demo dataset is loaded or generated automatically.
- Core KPIs render correctly.
- Trend and channel mix charts render correctly.
- Promotion comparison and MMM readiness tables render correctly.
- Tests cover reusable dashboard metrics.

