# Phase 25 - Customer and Cohort Intelligence

## Purpose

Phase 25 turns the Phase 24 customer data model into usable lifecycle analytics. The goal is to connect
marketing acquisition quality with customer behaviour and margin before moving into CLV, lapse risk, and
CRM incrementality.

## What Changed

- Added reusable customer analytics for KPIs, RFM-style segments, acquisition channel quality, monthly
  cohort retention, and new-vs-returning order economics.
- Added a Streamlit dashboard section for customer and cohort intelligence.
- Added tests covering customer economics, segment summaries, acquisition quality, cohort curves, and
  first-order vs repeat-order splits.

## Metrics Added

- Total customers.
- Repeat purchase rate.
- Customer revenue.
- Gross margin.
- Contactable rate.
- Gross margin per customer by acquisition channel.
- Repeat purchase rate by acquisition channel.
- Lifecycle and value segment summaries.
- Monthly acquisition cohort retention.
- New vs returning order revenue, margin, discounts, and refunds.

## Methodology Notes

The analytics are deliberately deterministic at this stage. This phase does not predict CLV or lapse risk yet.
It creates transparent customer-quality diagnostics that can be validated before adding more model-driven
customer decisions.

The most important commercial lens is margin quality, not revenue alone. This keeps the project aligned with
the broader goal: recommending growth actions that are defensible, profitable, and evidence-aware.

## Next Step

Phase 26 should add empirical CLV and lapse-risk baselines using temporal validation. The first version should
remain explainable: cohort-based future margin, days-since-order rules, and simple segment-level risk scoring
before any heavier model is introduced.
