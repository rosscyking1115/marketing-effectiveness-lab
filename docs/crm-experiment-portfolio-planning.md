# Phase 32 - CRM Experiment Portfolio Planning

## Purpose

Phase 32 moves CRM testing from single-experiment review into portfolio planning. The dashboard can now rank the current CRM experiment candidates and summarize the operational impact of launching the top experiments together.

## What Changed

- Added CRM experiment portfolio summary logic on top of ranked experiment artifacts.
- Added a portfolio CSV export for the selected top-ranked experiments.
- Added a Streamlit portfolio planner for current CRM experiment candidates.
- Added portfolio KPIs for experiment count, contactable audience, treatment audience, holdout audience, holdout rate, expected margin, risk-weighted margin, and portfolio status.
- Added tests for portfolio aggregation and export.

## Portfolio Status Logic

The planner returns an interpretable status:

- `Launch-ready portfolio` when all selected experiments are ready to test.
- `Mixed readiness` when ready tests and directional pilots are combined.
- `Pilot queue` when underpowered experiments are included.
- `Holdout burden review` when the selected portfolio creates high holdout exposure.
- `Review before launch` when a selected experiment should not launch or has no expected margin.

## Why It Matters

CRM teams rarely choose one retention test in isolation. They need to decide how many tests can run at once, how many customers are held out, and whether the expected margin is worth the operational complexity. This phase makes that trade-off visible.

## Production Boundary

The current workflow is deterministic and file-ready, but it is not a production campaign scheduler. A production version would coordinate mutually exclusive audiences, frequency caps, CRM platform activation, approval records, and experiment calendar conflicts.

## Next Step

Phase 33 should add overlap and eligibility rules so CRM experiment portfolios can detect conflicting audiences before launch.
