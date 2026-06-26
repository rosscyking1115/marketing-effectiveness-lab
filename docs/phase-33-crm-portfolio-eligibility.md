# Phase 33 - CRM Portfolio Eligibility And Overlap Checks

## Purpose

Phase 33 adds launch guardrails to the CRM experiment portfolio planner. The dashboard now checks whether a selected set of CRM experiments is operationally clean enough to launch together.

## What Changed

- Added deterministic eligibility checks for ranked CRM experiment portfolios.
- Added exact duplicate segment detection.
- Added broad targeting overlap checks for repeated lifecycle and value segments.
- Added launch-readiness checks for underpowered or non-launchable tests.
- Added holdout burden checks for high customer exposure.
- Added measurement-isolation checks for portfolios that need exclusions or send priority.
- Added Streamlit tables and CSV export for the eligibility checks.
- Added tests for blocked duplicate segment portfolios.

## Guardrail Checks

The eligibility table returns:

- `Segment uniqueness` - blocks duplicate exact segment designs.
- `Broad targeting overlap` - flags repeated lifecycle or value targeting.
- `Launch readiness` - flags underpowered or blocked tests.
- `Holdout burden` - flags portfolios with high holdout exposure.
- `Measurement isolation` - flags portfolios that need mutual exclusions or priority rules.

## Why It Matters

Experiment portfolios can look profitable in aggregate while still being hard to operate. CRM teams need to know whether experiments compete for the same audience definition, whether measurement remains clean, and whether too many customers are being held out at once.

## Production Boundary

These checks are deterministic portfolio guardrails, not a full CRM audience resolver. A production version would join customer-level audience membership, apply contact policy, exclude active tests, enforce frequency caps, and publish eligibility files to the CRM platform.

## Next Step

Phase 34 should add customer-level audience files for selected CRM experiments, including treatment and holdout assignment exports.
