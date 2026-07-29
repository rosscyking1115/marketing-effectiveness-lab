# Phase 16: Real-Data Connector Templates

## Objective

Make the project more real-data-ready by adding templates for common marketing and commerce exports.

The current app still models a single weekly MMM-ready dataset. This phase adds upstream connector contracts so an analyst can validate source exports before assembling that weekly dataset.

## What Was Added

The project now includes connector templates for:

- GA4 traffic and conversion exports.
- Google Ads weekly exports.
- Meta Ads weekly exports.
- Shopify or ecommerce orders exports.
- CRM and lifecycle marketing exports.

Each connector has:

- Required column definitions.
- Sample rows.
- Downloadable CSV template.
- Validation for missing fields, invalid week-start dates, nulls, non-numeric metrics, and negative values.

## Dashboard Behavior

The sidebar now includes a `Connector templates` expander.

An analyst can:

- Select an export type.
- Download the expected CSV template.
- Review the connector schema.
- Upload an exported CSV and validate it in memory.

## Why This Matters

Marketing effectiveness work usually fails before modeling if source data is messy.

This phase shows that the project understands the practical data engineering layer around MMM:

- Web analytics data.
- Paid media platform data.
- Ecommerce revenue data.
- CRM and lifecycle data.
- Contract validation before modeling.

## Security and Privacy Guardrails

The connector workflow does not ask for API keys.

Uploaded connector CSVs are parsed in memory in the current Streamlit prototype. They are not persisted by the app.

Before production use with private business data, the project should add authentication, storage controls, retention policy, audit logging, and secrets management.

## Future Product Path

A stronger next version should add:

- A weekly assembly pipeline from connector exports into the MMM schema.
- Source-specific mapping rules for channel spend and outcomes.
- dbt models for governed marketing marts.
- Warehouse connectors for BigQuery, Snowflake, or Postgres.
- Data quality reports by source and week.

## Phase 16 Done Criteria

Phase 16 is complete when:

- Connector template utilities exist in reusable package code.
- The dashboard exposes connector template downloads and validation.
- Tests cover template generation and validation failures.
- Documentation explains how connector exports relate to the weekly MMM dataset.
