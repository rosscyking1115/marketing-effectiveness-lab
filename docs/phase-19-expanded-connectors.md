# Phase 19: Expanded Connector Coverage

## Objective

Make the connector workflow cover more of the channels a retail or fashion marketing team would expect in a real measurement project.

Phase 18 made source diagnostics visible before modeling. Phase 19 expands the source contracts and assembly mappings for display, affiliate, influencer, and external-control inputs.

## What Was Added

The connector catalog now includes:

- Display ads weekly export.
- Affiliate network weekly export.
- Influencer weekly export.
- External controls weekly export.

The weekly assembly pipeline now maps:

- Display `spend_gbp` to `display_spend_gbp`.
- Affiliate `commission_gbp` plus `network_fee_gbp` to `affiliates_spend_gbp`.
- Influencer `fee_gbp`, `usage_rights_gbp`, and `paid_boost_gbp` to `influencer_spend_gbp`.
- External `consumer_confidence_index` and `inflation_rate_pct` into the weekly control columns.

Missing optional channel connectors still default to zero spend. Missing external-control connectors default to neutral zero placeholders.

## Dashboard Behavior

The existing connector template selector and connector assembly uploader automatically expose the expanded connector list because they read from the shared connector catalog.

Analysts can now validate these exports, assemble them into the weekly MMM-ready dataset, inspect diagnostics, and download the assembled CSV.

## Why This Matters

Display, affiliates, influencer, and macro controls often sit outside the clean paid-search and paid-social exports that early marketing projects start with. Adding these inputs makes the project feel closer to a realistic marketing measurement workflow:

- More complete media coverage.
- Clear cost definitions for non-platform channels.
- Explicit external controls for market conditions.
- Better diagnostics when a channel is absent versus truly inactive.

## Phase 19 Done Criteria

Phase 19 is complete when:

- Expanded connector templates exist in reusable package code.
- Assembly maps optional channel and control sources into the weekly MMM schema.
- Tests cover template validation and source-to-weekly mapping.
- Documentation and the public data contract reflect the expanded connector coverage.
