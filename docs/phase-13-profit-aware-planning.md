# Phase 13: Profit-Aware Scenario Planning

## Objective

Make the budget planner more commercially useful by adding a profit lens.

Earlier planner phases estimated media contribution and ROI. Phase 13 adds gross-margin-adjusted contribution profit so budget scenarios can be judged by estimated profit impact, not only revenue contribution.

## What Was Added

The planner now calculates:

- Current and proposed weekly gross profit from modeled contribution.
- Current and proposed weekly profit after media spend.
- Weekly profit change.
- Proposed profit ROI.
- Incremental profit ROI for budget increases.

## Dashboard Behavior

The Budget Scenario Planner now includes a gross margin assumption slider.

The scenario KPI row includes:

- Current weekly spend
- Proposed weekly spend
- Estimated contribution lift
- Estimated profit lift
- Profit ROI

The channel table now includes profit-after-media and profit-change fields alongside contribution and ROI fields.

## Why This Matters

Marketing teams often optimize toward revenue or ROAS because those metrics are visible. Commercial teams usually need a harder question:

Will this budget move improve contribution profit after media cost?

This phase makes the project more relevant to retail, ecommerce, and commercial data science roles because it connects MMM output to margin-aware decision making.

## Interpretation Guardrails

The current profit layer uses a single gross margin assumption.

It does not yet account for:

- Product/category margin mix
- Returns
- Fulfillment and payment costs
- Inventory constraints
- Channel capacity constraints
- Long-term brand effects

The metric is still useful as a directional planning view because it avoids treating every pound of modeled revenue as equally valuable.

## Future Product Path

A stronger product version should support:

- Category-specific margin assumptions
- New versus returning customer economics
- Contribution margin by product group
- Inventory-aware budget caps
- Profit-aware optimization objectives
- Scenario approval workflow

## Phase 13 Done Criteria

Phase 13 is complete when:

- Budget scenarios include margin-adjusted profit metrics.
- The dashboard exposes the gross margin assumption.
- Executive summaries mention profit impact.
- Tests cover profit calculations and margin validation.
