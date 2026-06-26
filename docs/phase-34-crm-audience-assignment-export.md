# Phase 34 - CRM Audience Assignment Export

## Purpose

Phase 34 turns a selected CRM experiment brief into a deterministic customer-level assignment file. The dashboard can now export treatment and holdout audiences for the selected experiment using demo customer IDs.

## What Changed

- Added deterministic customer-level treatment and holdout assignment.
- Added assignment logic based on artifact ID and customer ID hashing.
- Added preferred contact channel selection from email and SMS opt-in flags.
- Added audience summary metrics for treatment, holdout, holdout rate, email reach, and SMS reach.
- Added a Streamlit audience assignment preview and CSV download.
- Added tests for determinism, contactability, assignment counts, and CSV shape.

## Export Fields

The audience export includes:

- Artifact ID and segment label
- Customer ID
- Experiment group: treatment or holdout
- Assignment rank and deterministic assignment score
- Preferred contact channel
- Email and SMS opt-in flags
- Lapse-risk, lifecycle, and value segment fields
- Expected future margin and customer value diagnostics
- Eligibility status and exclusion reason

## Why It Matters

This closes the loop from analysis to activation. A commercial data scientist should not only recommend a test, but also produce a reproducible launch file that preserves holdout measurement and can be reviewed before CRM activation.

## Production Boundary

The current export uses demo customer IDs and deterministic assignment logic. Production use would require identity resolution, consent enforcement, suppression lists, campaign calendar checks, secure storage, approval logging, and CRM platform upload controls.

## Next Step

Phase 35 should add portfolio-level audience exports with mutual exclusion priority, so multiple selected CRM tests can be assigned without customer overlap.
