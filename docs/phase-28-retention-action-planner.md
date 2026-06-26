# Phase 28 - Retention Action Planner

## Purpose

Phase 28 connects customer value, lapse risk, and CRM incrementality into a segment-level retention action
planner. The goal is to show how a commercial data scientist can move from diagnostics to governed CRM
decisions without pretending the model has customer-level causal certainty.

## What Changed

- Added `retention_segment_action_plan` for segment-level CRM planning.
- Combined expected future margin, lapse-risk score, contactability, and matching CRM holdout evidence.
- Added recommended actions: Scale tested CRM, Run holdout test, Retest offer before scaling, Suppress incentive,
  Monitor, and No contactable audience.
- Added recommended holdout rates and maximum incentive cost per customer.
- Added a Streamlit dashboard section for retention priorities and segment action planning.

## Methodology

The planner works at segment grain:

- Segment value comes from expected 180-day future gross margin.
- Segment urgency comes from lapse-risk score.
- Segment opportunity is risk-weighted future margin.
- CRM evidence is matched from campaigns targeting the same lifecycle or value segment.
- Incentive guidance is capped as a share of expected future margin and set to zero for monitor/suppression cases.

The output is intentionally a planning layer. It recommends where to scale, test, retest, suppress, or monitor;
it does not claim to personalize offers at individual customer level.

## Why It Matters

This phase makes the customer layer feel like a usable commercial tool. It links CLV-style economics,
retention risk, CRM incrementality, contactability, and margin guardrails into one decision surface.

## Next Step

Phase 29 should add a lightweight CRM experiment design view: sample size, holdout split, success metric,
guardrails, and pre/post launch checklist for a chosen retention segment.
