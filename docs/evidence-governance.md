# Phase 12: Experiment Evidence Governance

## Objective

Add governance around experiment evidence before it calibrates MMM outputs.

Phase 11 made lift-test evidence uploadable. Phase 12 adds a review layer so the analyst can separate usable, approved evidence from tests that need investigation.

## What Was Added

The calibration layer now supports:

- Evidence quality scoring.
- Quality tiers for uploaded and demo lift tests.
- Review flags for weak or risky evidence.
- Approval-status handling.
- Approved-only filtering before calibration.

## Quality Signals

Each lift-test row is scored using:

- Test duration
- Observed lift interval width
- Metadata completeness
- Size of the MMM-versus-experiment mismatch

The score is translated into:

- `Strong`
- `Usable`
- `Needs review`

## Review Flags

The evidence review can flag:

- Short tests
- Wide intervals
- Large MMM mismatch
- Sparse metadata

These flags are intentionally simple. They make the dashboard behave more like a real marketing effectiveness workflow where evidence is reviewed before it changes model outputs.

## Dashboard Behavior

The Incrementality Calibration section now shows an evidence quality review table.

By default, calibration uses only evidence rows with an approved status. The analyst can disable the filter for exploration, but the product makes the governance default clear.

## Why This Matters

This phase makes the tool more credible.

In industry, an incrementality readout is not automatically trusted just because it exists. Analysts usually review test design, precision, market setup, audience setup, measurement window, and stakeholder sign-off before using it to calibrate MMM.

## Future Product Path

A production experiment registry should add:

- Persistent experiment records
- Approval workflow by role
- Evidence versioning
- Links to experiment design docs
- Calibration-job audit logs
- Separation between draft evidence and model-approved evidence

## Phase 12 Done Criteria

Phase 12 is complete when:

- Lift tests receive quality scores and tiers.
- Weak tests receive review flags.
- Approval status controls calibration eligibility.
- The dashboard shows evidence quality before calibration.
- Tests cover scoring, flags, and approved-only filtering.
