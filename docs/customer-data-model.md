# Phase 24 - Customer Data Model

## Purpose

Phase 24 adds the customer and CRM data foundation for the next expansion of Marketing Effectiveness Lab.
The weekly MMM dataset remains the marketing measurement spine, while the new customer tables create a
separate customer/order/campaign grain for lifecycle, cohort, CRM, and profit analysis.

## New Demo Tables

The generated customer demo exports are:

- `customers.csv`
- `orders.csv`
- `order_items.csv`
- `returns.csv`
- `crm_campaigns.csv`
- `crm_events.csv`
- `customer_segments.csv`
- `customer_ground_truth_metadata.json`

These files are synthetic and anonymized. They are not copied from a real retailer and should be treated as
safe portfolio demo data.

## Data Grains

The project now keeps two distinct data grains:

- Weekly marketing grain: MMM, media spend, revenue, controls, budget planning.
- Customer decision grain: customers, orders, items, returns, CRM campaigns, campaign events, lifecycle segments.

Keeping the grains separate prevents customer-level CRM logic from being forced into the weekly MMM schema.
Future phases can roll selected customer aggregates back into weekly reporting where useful.

## Validation Coverage

The customer schema validator checks:

- Required columns.
- Unique primary keys.
- Date, numeric, flag, and allowed-value fields.
- Non-negative commercial measures.
- Foreign keys across customers, orders, items, returns, CRM campaigns, events, and segments.
- One segment snapshot row per customer.

## Why It Matters

This creates the foundation for moving from channel-level effectiveness toward customer-level growth
decision support. The next phases can add RFM, cohort retention, empirical CLV, lapse risk, CRM
incrementality, and profit-aware customer recommendations without weakening the existing MMM workflow.
