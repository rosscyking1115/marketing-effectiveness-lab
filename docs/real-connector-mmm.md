# Phase 44 - Real connector data through the MMM assembly pipeline

Phase 41 ran the customer analytics on real data. This phase extends real data to the
**MMM data-ingestion path**: it derives a real weekly Shopify/ecommerce **outcome**
connector from the UCI Online Retail II transactions and runs it through the connector
assembly and source-diagnostics pipeline.

## What it does

`data/online_retail.build_shopify_connector_from_online_retail` aggregates the raw
transactions into the `shopify` connector template - weekly gross sales, orders, returns
(from cancellation invoices), net sales, new-customer orders, and AOV, on Monday
week-starts. `scripts/build_public_mmm_dataset.py` feeds it through
`assemble_weekly_dataset_from_connectors` and `assembled_weekly_diagnostics`, then writes
the connector, the assembled weekly dataset, the diagnostics, and a summary to
`data/public/` (git-ignored).

```powershell
uv run --group data python scripts/build_public_mmm_dataset.py
```

## What a real run shows

A representative run assembled ~104 real weekly rows (Nov 2009 - Dec 2011), ~GBP 19.4M
net revenue, ~40k orders. The diagnostics correctly report the outcome source as covered
and **flag the media-coverage gap** ("no non-zero media spend channels"), and surface a
real continuity break in the source weeks - exactly the data-quality signals the pipeline
is meant to raise.

## Scope and honesty

This validates the **connector contract, assembly, and diagnostics on real outcome data**.
It does **not** validate MMM channel attribution: real, public, weekly spend-by-channel
data does not exist (the MMM tooling ecosystem ships simulated data for this reason), so
the paid-media connectors are absent and assembled media spend is zero. Supplying a real
ad-platform spend export is the remaining step to validate the attribution half - and the
pipeline is already shaped to ingest it the moment such an export is available.
