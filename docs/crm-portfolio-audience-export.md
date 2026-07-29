# Phase 35 - CRM Portfolio Audience Export

## Purpose

Phase 35 extends the single-experiment audience export into a portfolio-level launch file. Analysts can select the top ranked CRM experiments and export one mutually exclusive customer assignment file across the selected portfolio.

## What Changed

- Added deterministic portfolio-level audience assignment.
- Added mutual exclusion priority based on experiment rank.
- Suppressed customers already assigned to a higher-priority CRM experiment.
- Added portfolio audience summary metrics for assigned customers, suppressed overlap, treatment, holdout, and export status.
- Added a Streamlit portfolio audience preview and CSV download.
- Added tests for deterministic output, unique customer assignment, priority ordering, suppression accounting, and CSV shape.

## Assignment Rules

The portfolio export:

- Ranks experiments using the CRM artifact comparison table.
- Builds each experiment's deterministic treatment/holdout audience.
- Assigns customers to the highest-priority experiment they qualify for.
- Excludes duplicate customer exposure from lower-priority experiments.
- Preserves each experiment's treatment and holdout labels after exclusion.

## Why It Matters

This moves the project closer to a real CRM operating workflow. A team can now plan a set of tests, review eligibility guardrails, and export a single customer-level launch file that avoids overlapping customer exposure.

## Production Boundary

The current workflow uses demo customer IDs and deterministic local assignment. A production version would need governed customer identity mapping, live consent checks, suppression lists, frequency caps, campaign calendar rules, secure file delivery, and CRM platform activation logs.

## Next Step

Phase 36 should add experiment calendar planning so portfolio audiences can be staged across launch windows and avoid contact fatigue.
