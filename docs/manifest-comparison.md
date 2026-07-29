# Phase 23 - Model-Run Manifest Comparison

## Purpose

Phase 23 turns the model-run manifest from a single-run export into a lightweight scenario review workflow.
Analysts can download JSON manifests from different dashboard settings, then upload them back into the app
to compare readiness, model diagnostics, and commercial impact side by side.

## What Changed

- Added validated parsing for model-run manifest JSON artifacts.
- Added a ranked comparison table for uploaded manifests.
- Added CSV export for the comparison table.
- Surfaced the workflow in the Streamlit executive summary area, next to the report and manifest downloads.

## Review Logic

The comparison ranks artifacts by:

1. Recommendation readiness score.
2. Estimated weekly profit change.
3. Holdout MAPE, with lower error preferred.

The output keeps the important review fields visible: run ID, readiness status, profit lift, profit ROI,
holdout MAPE, top contribution channel, data source, and active model label.

## Why It Matters

This is a small product step toward governed model-run tracking. It shows how an MMM dashboard can move
from exploratory analysis into repeatable review artifacts without requiring a production database yet.

Future production versions would persist manifests, attach user identity, record approval decisions, and
compare runs over time by brand, market, campaign period, and model version.
