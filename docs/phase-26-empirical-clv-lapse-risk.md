# Phase 26 - Empirical CLV and Lapse-Risk Baselines

## Purpose

Phase 26 adds explainable customer value and lapse-risk baselines. It extends the customer intelligence layer
from descriptive cohort analytics into decision-support inputs for future CRM and retention planning.

## What Changed

- Added cumulative customer value windows after first purchase: 30, 60, 90, and 180 days.
- Added a historical 180-day future-margin backtest by lifecycle and value segment.
- Added current customer scoring for expected future gross margin and lapse-risk band.
- Added dashboard views for acquisition-channel value windows, lapse-risk/value segments, and segment
  backtest diagnostics.

## Methodology

The baseline remains deliberately transparent:

- Customer value is measured as gross margin, not revenue alone.
- Lapse risk uses recency, frequency, value segment, and discount dependency.
- Expected 180-day future margin is calibrated from a historical segment-level backtest.
- The output is directional decision support, not a production churn or personalization model.

## Why It Matters

This phase gives the project a customer economics spine. MMM can suggest where budget should move, while
customer CLV and lapse diagnostics show whether acquisition and retention activity is creating durable margin.

## Next Step

Phase 27 should add CRM incrementality measurement using campaign target/holdout events. That will let the
project estimate whether lifecycle campaigns create incremental profit rather than only reporting campaign
response or attributed revenue.
