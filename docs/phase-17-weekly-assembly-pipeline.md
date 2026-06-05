# Phase 17: Weekly Connector Assembly Pipeline

## Objective

Turn validated connector exports into the documented weekly MMM-ready dataset.

Phase 16 made source templates available. Phase 17 closes the next practical gap: an analyst can now upload platform exports, assemble a weekly dataset, download it for review, and use it in the dashboard when enough weekly history is available.

## What Was Added

The reusable package now includes `src/marketing_effectiveness_lab/data/assembly.py`.

It provides:

- Connector CSV validation before assembly.
- Shopify/ecommerce as the reconciled revenue and order source.
- Weekly aggregation by Monday `week_start`.
- Channel spend mapping for Google Ads, Meta Ads, and CRM.
- Organic search session mapping from GA4 source/medium rows.
- Promotion depth derived from ecommerce discounts and gross sales.
- Holiday and season flags derived from the weekly date.
- Final validation against the same weekly schema used by uploaded CSVs and demo data.

## Dashboard Behavior

The sidebar data source selector now includes `Connector assembly`.

An analyst can upload:

- Shopify or ecommerce orders export.
- GA4 traffic and conversion export.
- Google Ads weekly export.
- Meta Ads weekly export.
- CRM and lifecycle export.

The app then:

- Shows a source summary table.
- Reports connector or final weekly-schema validation errors.
- Offers a downloadable assembled weekly CSV.
- Runs the dashboard on the assembled dataset when at least 57 weekly rows are available for the current holdout modeling workflow.

## Current Mapping

| Source | Output |
| --- | --- |
| Shopify/ecommerce `net_sales_gbp` | `revenue_gbp` |
| Shopify/ecommerce `orders` | `orders` |
| Shopify/ecommerce `new_customer_orders` | `new_customers` |
| Shopify/ecommerce discounts and gross sales | `promotion_depth_pct` and `promotion_flag` |
| Google Ads `cost_gbp` | `paid_search_spend_gbp` |
| Meta Ads `spend_gbp` | `paid_social_spend_gbp` |
| CRM `cost_gbp` | `email_spend_gbp` |
| GA4 organic source/medium sessions | `organic_search_sessions` |

Display, affiliates, and influencer spend remain explicit zero defaults until those source contracts are added.

## Why This Matters

This moves the project closer to real marketing analytics work.

Most MMM projects need a governed path from messy platform exports to a weekly modeling table. This phase shows:

- Source contract validation.
- Outcome reconciliation.
- Channel mapping.
- Data quality feedback before modeling.
- A path from dashboard demo to usable analyst workflow.

## Phase 17 Done Criteria

Phase 17 is complete when:

- Connector assembly exists in reusable package code.
- Tests cover successful assembly, missing outcome source, connector validation failures, and final weekly-schema failures.
- The Streamlit app exposes connector assembly as a data source.
- Documentation explains the source-to-weekly mapping.
