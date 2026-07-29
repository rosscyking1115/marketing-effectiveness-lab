# Phase 11: Experiment Evidence Upload

## Objective

Move incrementality calibration from demo-only evidence to a real-data-ready experiment workflow.

This phase adds a lift-test CSV contract so analysts can upload experiment readouts and use them to calibrate MMM contribution, ROI, and uncertainty diagnostics.

## What Was Added

The calibration layer now supports:

- A downloadable lift-test CSV template.
- Upload validation for experiment evidence.
- Required fields for channel, experiment type, test duration, modeled lift, observed lift, and observed lift interval.
- Optional metadata for test name, dates, market, confidence level, owner, and notes.
- Dashboard selection between demo evidence and uploaded evidence.

## Required CSV Fields

- `channel`
- `experiment_type`
- `weeks`
- `model_lift_gbp`
- `observed_lift_gbp`
- `observed_lift_lower_gbp`
- `observed_lift_upper_gbp`

## Optional CSV Fields

- `test_name`
- `start_date`
- `end_date`
- `market`
- `confidence_level`
- `approval_status`
- `owner`
- `source_notes`

## Why This Matters

This makes the project much stronger than a static portfolio dashboard.

In real marketing effectiveness work, MMM needs to be reconciled with causal evidence. A serious workflow should let the analyst bring in geo experiments, platform conversion-lift studies, matched-market tests, or incrementality studies, then compare those readouts against modeled lift.

## Product Direction

The CSV upload is an intentionally simple first version. The future SaaS-style version should evolve into an experiment registry with:

- Persisted experiment records
- User permissions
- Evidence approval status
- Market and audience definitions
- Test methodology tags
- Audit history
- Links to reports or notebooks
- Model calibration jobs triggered by approved evidence

## Phase 11 Done Criteria

Phase 11 is complete when:

- A lift-test CSV template is available.
- Uploaded lift-test CSVs are parsed and validated.
- Invalid experiment evidence returns clear errors.
- Valid uploaded evidence can replace demo evidence in the dashboard.
- Tests cover template generation, parser validation, and error cases.
