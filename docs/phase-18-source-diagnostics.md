# Phase 18: Source Diagnostics

## Objective

Make connector assembly safer and more useful by showing data-quality diagnostics before modeling.

Phase 17 assembled validated platform exports into the weekly MMM schema. Phase 18 adds a source diagnostics layer so analysts can quickly see whether the assembled dataset is ready for modeling or needs data cleanup.

## What Was Added

The reusable package now includes `src/marketing_effectiveness_lab/data/diagnostics.py`.

It checks:

- Final weekly schema status.
- Weekly history length.
- Revenue and order positivity.
- New-customer counts versus total orders.
- Active media channel coverage.
- Organic search availability.
- Zero-default channel notes for display, affiliates, and influencer.
- Source coverage by uploaded connector.

## Dashboard Behavior

The `Connector assembly` workflow now shows an `Assembly diagnostics` table after source upload and assembly.

Diagnostic statuses use:

- `Pass`: ready for the current workflow.
- `Review`: usable for exploration, but the analyst should inspect the issue.
- `Block`: should not proceed to modeling until fixed.
- `Info`: expected limitation or current default.

This table appears before the app decides whether to continue to the full dashboard or stop because of validation errors or insufficient weekly history.

## Why This Matters

Real MMM projects usually need judgment before modeling:

- Is the ecommerce source reliable enough to be the outcome?
- Do platform exports cover the same weeks?
- Are channels missing because they are truly zero, or because no connector exists yet?
- Is there enough weekly history for holdout diagnostics?

This phase makes that judgment explicit in the product.

## Phase 18 Done Criteria

Phase 18 is complete when:

- Diagnostics exist in reusable package code.
- Tests cover schema, history, media coverage, organic search, source coverage, and anomaly checks.
- Streamlit shows diagnostics during connector assembly.
- Documentation explains the diagnostic statuses and why they matter.
