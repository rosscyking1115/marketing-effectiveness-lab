# Phase 27 - CRM Incrementality Diagnostics

## Purpose

Phase 27 adds campaign-level CRM incrementality diagnostics using the target and holdout events created by
the customer data layer. The goal is to move beyond attributed campaign revenue and estimate whether lifecycle
activity appears to create incremental profit.

## What Changed

- Added target-vs-holdout conversion lift by CRM campaign.
- Added normal-approximation uncertainty intervals for conversion lift.
- Added incremental margin, campaign cost, incentive cost, and incremental profit estimates.
- Added campaign evidence statuses for Positive, Review, Negative, and Needs more data readouts.
- Added a Streamlit dashboard section showing portfolio metrics, campaign profit, and campaign-level details.

## Methodology

Each campaign compares customers assigned to the treatment group with customers assigned to the holdout group:

- Conversion lift = treatment conversion rate minus holdout conversion rate.
- Incremental conversions = conversion lift multiplied by target customers.
- Incremental margin = treatment margin per customer minus holdout margin per customer, scaled to target customers.
- Incremental profit = incremental margin minus fixed campaign cost and per-sent-customer incentive cost.

The evidence status is intentionally conservative. A campaign is marked Positive only when the lower bound of
the conversion lift interval is above zero and incremental profit is positive.

## Why It Matters

CRM and retention teams can easily overstate impact when they only report attributed revenue. This phase gives
the project a commercially credible holdout-test readout that connects lifecycle marketing to margin, cost, and
decision governance.

## Next Step

Phase 28 should connect these CRM incrementality readouts to retention planning. A useful next increment would
rank high-lapse-risk customers by expected future margin and estimate which segments are most suitable for CRM
treatment, holdout testing, or suppression.
