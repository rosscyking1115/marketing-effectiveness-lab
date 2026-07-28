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

### Correction: the backtest error was in-sample

As first written, `customer_future_value_backtest()` set each segment's expected future margin to
the mean of the actual future margins *of the customers it then scored*. `mean_absolute_error_gbp`
was therefore mean absolute deviation around a within-segment mean, not forecast error, and
`expected_future_margin_gbp` matched `avg_actual_future_margin_gbp` exactly by construction. The
number could not come out badly, so it was not evidence of anything.

It now uses two non-overlapping windows. Segment expectations are estimated on the 180 days before
a fit cutoff (default: one horizon before `cutoff_date`) and scored against realised margin in the
180 days after `cutoff_date`. Segments that appear at evaluation but not in the fit window fall
back to the pooled fit-window mean rather than to their own labels.

`baseline_mean_absolute_error_gbp` was added alongside it: the same error for a model that predicts
the pooled fit-window average for every customer. It gives the segmentation something to lose to,
and on the demo data it does lose in places. On the default generated customer set (seed 42, 2,400
customers, cutoff 2025-01-01, 180-day horizon), customer-weighted segment expectations beat the
pooled baseline overall — £4.64 against £6.82 — but every New and Active segment is *worse* than
the baseline (New/VIP: £17.77 against £11.92), and the win comes entirely from Lapsing and Dormant
segments, where the right answer is close to zero and easy. On the UCI Online Retail II public
dataset the segmentation wins more clearly, £371.95 against £475.62. `test_customer_future_value_backtest_expectation_is_out_of_sample`
guards against the original defect returning.

## Why It Matters

This phase gives the project a customer economics spine. MMM can suggest where budget should move, while
customer CLV and lapse diagnostics show whether acquisition and retention activity is creating durable margin.

## Next Step

Phase 27 should add CRM incrementality measurement using campaign target/holdout events. That will let the
project estimate whether lifecycle campaigns create incremental profit rather than only reporting campaign
response or attributed revenue.
