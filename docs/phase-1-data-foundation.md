# Phase 1: Data Foundation

## Objective

Build a credible weekly marketing dataset and data contract for a UK fashion ecommerce business.

The dataset should be good enough to support analyst dashboarding, econometric modeling, MMM, and budget optimization.

## Why Start Here

Marketing mix modeling is only as credible as the data foundation. A polished dashboard cannot compensate for weak channel definitions, missing control variables, unclear time grain, or unrealistic business assumptions.

Phase 1 focuses on:

- A realistic business scenario
- A consistent weekly grain
- A replaceable data schema
- Validation checks
- Demo data that behaves like real retail marketing data

## Current Dataset

Generated file:

- `data/demo/fashion_retail_weekly.csv`

Supporting files:

- `data/demo/channel_spend_weekly_long.csv`
- `data/demo/ground_truth_metadata.json`

The generated dataset covers:

- UK fashion ecommerce
- Weekly reporting
- GBP currency
- 2023 to 2025
- Paid and owned marketing channels
- Revenue, orders, new customers, and AOV
- Promotions, holidays, seasonality, inflation, and consumer confidence controls

## Real Data Readiness

The lab is designed so the demo dataset can later be replaced by real company data.

A real import should provide the same core fields:

- Week start date
- Outcome metrics
- Channel spend
- Organic demand controls
- Promotion controls
- Seasonality and macro controls

Real ad-platform or ecommerce data can come from sources such as Google Ads, Meta Ads, Shopify, GA4, Klaviyo, affiliate platforms, or finance sales reports. Version 1 does not require API integrations; spreadsheet or CSV imports are enough.

## Phase 1 Done Criteria

Phase 1 is complete when:

- The demo dataset can be generated reproducibly.
- Required columns are documented.
- Validation checks catch missing, negative, duplicated, or non-weekly data.
- The generated data includes realistic marketing and commercial patterns.
- The data is ready for an analyst dashboard in Phase 2.

