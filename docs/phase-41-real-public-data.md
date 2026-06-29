# Phase 41 - Real public data validation

The customer-analytics layer was previously exercised only on deterministic synthetic
demo data. This phase runs it on a real, public dataset to show the pipeline works on
genuine purchase behaviour, not just generated numbers.

## Dataset

- **UCI Online Retail II** - transactions for a real UK-based online retailer,
  December 2009 to December 2011.
- Source: <https://archive.ics.uci.edu/dataset/502/online+retail+ii>
- Real, openly published, and priced in GBP, so it maps cleanly onto the existing
  customer/order schema.

## What it does

`scripts/load_public_data.py`:

1. Downloads the dataset (or reads a local `--raw-path`).
2. Maps it to the package `customers` and `orders` tables via
   `data/online_retail.build_customer_tables_from_online_retail`.
3. Validates the mapped tables against `customer_schema`.
4. Runs the real analytics - cohort retention, new-vs-returning, value windows,
   empirical CLV backtest, and lapse-risk scoring.
5. Writes the mapped tables and a provenance-documented `real_data_summary.md` to
   `data/public/` (git-ignored).

```powershell
uv run --group data python scripts/load_public_data.py
```

## What is real vs imputed

The adapter is explicit about provenance (`online_retail.dataset_provenance`).

- **Real**, taken straight from the transactions: order dates, per-order revenue,
  customer identity and therefore acquisition date, recency, repeat behaviour, country,
  and lifecycle status (derived from real recency).
- **Synthetic overlays**, because the dataset does not contain them: gross margin
  (a flat assumed rate), acquisition channel, and CRM email/SMS opt-in flags. These are
  assigned deterministically from a hash of the customer id purely to satisfy the schema.
  The headline cohort, value, CLV, and lapse analytics recompute lifecycle and value from
  the real orders, so they do not depend on these overlays.

Cancellation invoices (those starting with `C`) and rows without a customer id are
excluded: cancellations cannot be reliably linked to an originating order, and customer
analytics requires an identified customer.

## Example run

A representative run mapped ~5.9k customers and ~37k orders spanning the full period,
with an ~83% repeat-customer order share and a declining month-1 to month-6 retention
curve - all computed from real purchases.

## Scope note

This validates the **customer / CRM analytics** half on real data. The MMM weekly layer
still uses synthetic channel spend, because weekly spend-by-channel is not available in
public datasets; supplying a real connector export remains the path to validating that
half (see the data contract and connector templates).
