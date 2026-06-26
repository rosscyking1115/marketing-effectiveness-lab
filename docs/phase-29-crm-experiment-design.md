# Phase 29 - CRM Experiment Design

## Purpose

Phase 29 turns the retention action planner into a lightweight experiment design surface. It helps a reviewer
see how a recommended CRM segment would become a governed holdout test with audience sizing, success criteria,
guardrails, and launch checks.

## What Changed

- Added `crm_experiment_design` for one selected retention segment.
- Added approximate two-proportion sample-size guidance for a planned conversion lift.
- Added treatment and holdout audience sizing from the recommended holdout rate.
- Added launch readiness labels: Ready to test, Directional pilot, Underpowered, and Do not launch.
- Added `crm_experiment_checklist` for audience, randomization, measurement, guardrails, and decision readiness.
- Added a Streamlit section for segment selection, test audience split, metrics, and launch checklist.

## Methodology

The experiment design remains intentionally simple and reviewable:

- The audience comes from contactable customers in the selected retention segment.
- The holdout split comes from the retention planner recommendation.
- Required sample size uses a normal approximation for a two-proportion conversion test.
- The primary metric is incremental gross margin per contacted customer.
- Guardrails include unsubscribe rate, refund rate, discount rate, and gross margin rate.

The design can explicitly say that a segment is underpowered. This is a feature, not a failure: CRM teams often
need to distinguish a directional pilot from a statistically powered test.

## Why It Matters

This phase makes the project feel closer to real commercial analytics work. It links model output to an
operational test plan, while keeping the evidence standard honest enough for stakeholder review.

## Next Step

Phase 30 should package the customer and CRM workflow into a downloadable experiment brief or model-run artifact
so a user can export the chosen segment, test design, guardrails, and decision rule.
