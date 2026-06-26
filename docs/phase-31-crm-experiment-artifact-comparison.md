# Phase 31 - CRM Experiment Artifact Comparison

## Purpose

Phase 31 turns CRM experiment exports into a lightweight review workflow. Analysts can now download JSON artifacts from different segment designs, upload them back into the dashboard, and compare which experiment should be prioritised first.

## What Changed

- Added JSON parsing and validation for CRM experiment artifacts.
- Added a ranked comparison table for saved experiment artifacts.
- Ranked artifacts by launch readiness, expected incremental margin, risk-weighted segment value, audience size, and holdout burden.
- Added a downloadable comparison CSV for stakeholder review.
- Added a Streamlit comparison expander under the CRM experiment design section.
- Added tests for parsing, ranking, and CSV export.

## Comparison Fields

The comparison table includes:

- Artifact ID
- Segment label
- Recommended action
- Launch readiness
- Priority score
- Expected incremental margin at MDE
- Contactable customers
- Holdout customers
- Recommended holdout rate
- CRM evidence status

## Why It Matters

This moves the CRM workflow from a single generated brief into a small artifact governance loop. A reviewer can compare several possible retention tests and decide which one is commercially worth launching, which one is only a directional pilot, and which one creates too much holdout burden for the likely return.

## Production Boundary

The workflow is still local and file-based. A production version would store artifacts in a governed database, attach authenticated approvers, preserve audit history, and connect launches to CRM platforms.

## Next Step

Phase 32 should add CRM experiment portfolio planning, showing how many customers and how much expected margin are committed if several ranked experiments are launched together.
