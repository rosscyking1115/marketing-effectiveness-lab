# Phase 30 - CRM Experiment Brief Export

## Purpose

Phase 30 packages the selected CRM experiment design into downloadable review artifacts. This turns the
retention and experiment workflow from an on-screen diagnostic into something an analyst could share for
stakeholder review.

## What Changed

- Added a deterministic CRM experiment artifact with a stable artifact ID.
- Added a human-readable markdown CRM experiment brief.
- Added a machine-readable JSON export for the selected CRM experiment.
- Added Streamlit download buttons for both artifacts.
- Added tests for stable artifact IDs, JSON serialization, and markdown structure.

## Artifact Contents

The exported artifact includes:

- Segment definition and recommended action.
- Audience size, treatment count, holdout count, and holdout rate.
- Sample-size guidance, launch readiness, baseline conversion assumption, and minimum detectable lift.
- Primary success metric, success rule, and guardrail metrics.
- Launch checklist and review notes.

## Why It Matters

Real analytics products need durable review artifacts, not only dashboard screenshots. This phase gives the
customer and CRM workflow a lightweight governance surface: an analyst can download a brief, discuss the test,
and store a JSON artifact for comparison or future audit.

## Production Boundary

The artifact is downloadable and deterministic, but not persisted by the app. A production version should add
authenticated users, approval status, immutable audit logs, campaign IDs from the CRM platform, and secure
artifact storage.

## Next Step

Phase 31 should add comparison of saved CRM experiment artifacts, similar to the model-run manifest comparison
workflow, so users can compare candidate CRM tests by readiness, expected margin, and audience size.
