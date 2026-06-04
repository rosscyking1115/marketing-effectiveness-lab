# Phase 10: Incrementality Calibration

## Objective

Connect MMM output to causal experiment evidence.

This phase adds a practical calibration layer that compares modeled channel lift with demo lift-test readouts, then calculates channel-level correction factors for contribution, ROI, and uncertainty intervals.

## Why This Matters

MMM is useful for broad allocation questions, but it can overstate or understate individual channels when channels are correlated, spend patterns move together, or important business drivers are missing.

Experiment calibration is how mature marketing analytics teams make MMM more trustworthy. Geo holdouts, conversion-lift studies, matched-market tests, and incrementality readouts can be used to anchor the model to causal evidence.

## What Was Added

The reusable calibration module can:

- Generate deterministic demo lift-test readouts from the active MMM model.
- Validate lift-test schema and numeric bounds.
- Aggregate multiple tests into channel-level calibration factors.
- Apply calibration factors to MMM contribution and ROI estimates.
- Apply calibration factors to contribution uncertainty intervals.

## Dashboard Outputs

The dashboard now includes an Incrementality Calibration section with:

- Demo lift-test readouts by channel.
- Experiment calibration factor chart.
- Optional calibrated contribution chart.
- Optional calibrated contribution, ROI, and uncertainty table.
- Clear caveat that the current planner still uses the active MMM response curves.

## Interpretation Guardrails

The current lift tests are demo readouts, not live business experiments.

The calibration factors are diagnostic and should be treated as an analyst workflow preview. In a production-grade tool, real experiment evidence should be stored with:

- Experiment design metadata
- Test and control definitions
- Lift calculation method
- Confidence or credible intervals
- Approval and audit history
- Links to campaign and market setup

## Future Product Path

The next stronger version would let users upload or register real lift tests, then use those readouts as priors or calibration targets in Bayesian MMM.

This would move the product toward a serious marketing effectiveness workflow:

1. Estimate MMM contribution and response curves.
2. Quantify model uncertainty.
3. Reconcile model outputs with causal experiments.
4. Use calibrated posterior estimates for budget optimization.
5. Export stakeholder-ready recommendations with caveats.

## Phase 10 Done Criteria

Phase 10 is complete when:

- Lift-test calibration utilities exist in reusable package code.
- Lift-test validation is covered by tests.
- Contribution and uncertainty calibration are covered by tests.
- The dashboard shows experiment evidence and optional calibrated outputs.
- Documentation explains how experiment calibration fits the MMM roadmap.
