"""Adapter from the UCI *Online Retail II* dataset to the customer-analytics schema.

Online Retail II is a real, public dataset of transactions for a UK-based online
retailer (2009-2011). It lets the customer/cohort/CLV analytics in this package run
on genuine purchase behaviour instead of synthetic demo data.

What is real (taken directly from the transactions):

- ``order_date`` and per-order ``gross_revenue_gbp`` (the retailer prices in GBP)
- customer identity and therefore acquisition date, recency, repeat behaviour
- the customer's country and derived lifecycle status (from real recency)

What is a documented synthetic overlay (the dataset does not contain it):

- ``gross_margin_gbp`` -- imputed with a flat ``gross_margin_rate`` (no cost data)
- ``acquisition_channel`` and the CRM ``email_opt_in`` / ``sms_opt_in`` flags --
  assigned deterministically from a hash of the customer id, purely so the rows
  satisfy the schema. The headline analytics (cohort retention, value windows,
  CLV / lapse baselines) recompute lifecycle and value from the real orders, so
  they do not depend on these overlays.

Cancellation invoices (those whose number starts with ``C``) and rows without a
customer id are dropped: cancellations cannot be reliably linked back to an
originating order, and customer analytics requires an identified customer.
"""

from __future__ import annotations

import hashlib

import pandas as pd

from marketing_effectiveness_lab.data.customer_schema import (
    CUSTOMER_CHANNELS,
    LIFECYCLE_SEGMENTS,
)

# Source columns in the official UCI Online Retail II export.
RAW_COLUMNS = ("Invoice", "StockCode", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country")

DEFAULT_GROSS_MARGIN_RATE = 0.45


def build_customer_tables_from_online_retail(
    raw: pd.DataFrame,
    *,
    gross_margin_rate: float = DEFAULT_GROSS_MARGIN_RATE,
) -> dict[str, pd.DataFrame]:
    """Map raw Online Retail II rows to ``customers`` and ``orders`` tables.

    The returned tables follow ``customer_schema.CUSTOMER_TABLES`` for ``customers``
    and ``orders`` so the existing analytics functions accept them unchanged.
    """

    if not 0 <= gross_margin_rate <= 1:
        raise ValueError("gross_margin_rate must be between 0 and 1.")

    orders = _build_orders(raw, gross_margin_rate=gross_margin_rate)
    if orders.empty:
        raise ValueError("No usable sale invoices found in the Online Retail II export.")
    customers = _build_customers(raw, orders)
    return {"customers": customers, "orders": orders}


def build_shopify_connector_from_online_retail(raw: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw Online Retail II rows into a weekly Shopify/ecommerce connector export.

    The output matches the ``shopify`` connector template, so it can be fed straight into
    ``assemble_weekly_dataset_from_connectors`` as a real outcome source. Gross sales,
    orders, returns (from cancellation invoices), net sales, new-customer orders, and AOV
    are all derived from the real transactions; ``discounts_gbp`` is 0 because the source
    does not record order-level discounts.
    """

    missing = [column for column in RAW_COLUMNS if column not in raw.columns]
    if missing:
        raise ValueError(f"Online Retail II export is missing columns: {', '.join(missing)}")

    frame = raw.loc[:, list(RAW_COLUMNS)].copy()
    frame["Invoice"] = frame["Invoice"].astype(str).str.strip()
    frame["Quantity"] = pd.to_numeric(frame["Quantity"], errors="coerce")
    frame["Price"] = pd.to_numeric(frame["Price"], errors="coerce")
    frame = frame.dropna(subset=["Quantity", "Price", "InvoiceDate"])
    frame["line_revenue_gbp"] = frame["Quantity"] * frame["Price"]
    order_date = pd.to_datetime(frame["InvoiceDate"]).dt.normalize()
    # Monday of each transaction's week, per the weekly data contract.
    frame["week_start"] = order_date - pd.to_timedelta(order_date.dt.dayofweek, unit="D")
    frame["order_date"] = order_date
    is_cancellation = frame["Invoice"].str.upper().str.startswith("C")

    sales = frame[(~is_cancellation) & (frame["Quantity"] > 0) & (frame["Price"] > 0)]
    if sales.empty:
        raise ValueError("No usable sale invoices found in the Online Retail II export.")

    invoices = sales.groupby("Invoice").agg(
        week_start=("week_start", "min"),
        invoice_revenue_gbp=("line_revenue_gbp", "sum"),
    )
    invoices = invoices[invoices["invoice_revenue_gbp"] > 0]
    weekly = invoices.groupby("week_start").agg(
        gross_sales_gbp=("invoice_revenue_gbp", "sum"),
        orders=("invoice_revenue_gbp", "size"),
    )

    returns = (
        frame[is_cancellation].groupby("week_start")["line_revenue_gbp"].sum().abs().rename("returns_gbp")
    )

    identified = sales.dropna(subset=["Customer ID"]).copy()
    identified["Customer ID"] = pd.to_numeric(identified["Customer ID"], errors="coerce")
    identified = identified.dropna(subset=["Customer ID"])
    invoice_customer = identified.groupby("Invoice").agg(
        customer_id=("Customer ID", "first"),
        week_start=("week_start", "min"),
        order_date=("order_date", "min"),
    )
    first_order = invoice_customer.groupby("customer_id")["order_date"].transform("min")
    new_orders = invoice_customer[invoice_customer["order_date"] == first_order]
    weekly_new = new_orders.groupby("week_start").size().rename("new_customer_orders")

    weekly = weekly.join(returns, how="left").join(weekly_new, how="left").reset_index()
    weekly["returns_gbp"] = weekly["returns_gbp"].fillna(0.0)
    weekly["new_customer_orders"] = weekly["new_customer_orders"].fillna(0).astype(int)
    weekly["discounts_gbp"] = 0.0
    weekly["net_sales_gbp"] = (weekly["gross_sales_gbp"] - weekly["returns_gbp"]).clip(lower=0)
    weekly["average_order_value_gbp"] = weekly["gross_sales_gbp"] / weekly["orders"]

    for column in ["gross_sales_gbp", "discounts_gbp", "returns_gbp", "net_sales_gbp", "average_order_value_gbp"]:
        weekly[column] = weekly[column].round(2)
    weekly["orders"] = weekly["orders"].astype(int)
    weekly["week_start"] = weekly["week_start"].dt.strftime("%Y-%m-%d")

    columns = [
        "week_start",
        "gross_sales_gbp",
        "discounts_gbp",
        "returns_gbp",
        "net_sales_gbp",
        "orders",
        "new_customer_orders",
        "average_order_value_gbp",
    ]
    return weekly[columns].sort_values("week_start").reset_index(drop=True)


def dataset_provenance() -> dict[str, object]:
    """Return a machine-readable note on what is real versus imputed."""

    return {
        "source": "UCI Online Retail II (real UK online retailer, 2009-2011)",
        "source_url": "https://archive.ics.uci.edu/dataset/502/online+retail+ii",
        "real_fields": [
            "order_date",
            "gross_revenue_gbp",
            "customer identity / acquisition_date / recency / repeat behaviour",
            "country",
            "lifecycle_status (derived from real recency)",
        ],
        "imputed_fields": {
            "gross_margin_gbp": "flat gross_margin_rate (no cost data in source)",
            "acquisition_channel": "deterministic hash of customer id (schema overlay)",
            "email_opt_in / sms_opt_in": "deterministic hash of customer id (schema overlay)",
        },
        "excluded_rows": "cancellation invoices (Invoice starts with 'C') and rows without a customer id",
    }


def _build_orders(raw: pd.DataFrame, *, gross_margin_rate: float) -> pd.DataFrame:
    missing = [column for column in RAW_COLUMNS if column not in raw.columns]
    if missing:
        raise ValueError(f"Online Retail II export is missing columns: {', '.join(missing)}")

    frame = raw.loc[:, list(RAW_COLUMNS)].copy()
    frame["Customer ID"] = pd.to_numeric(frame["Customer ID"], errors="coerce")
    frame = frame.dropna(subset=["Customer ID"])
    frame["Invoice"] = frame["Invoice"].astype(str).str.strip()
    # Drop cancellation invoices; they cannot be linked to an originating order.
    frame = frame[~frame["Invoice"].str.upper().str.startswith("C")]
    frame["Quantity"] = pd.to_numeric(frame["Quantity"], errors="coerce")
    frame["Price"] = pd.to_numeric(frame["Price"], errors="coerce")
    frame = frame.dropna(subset=["Quantity", "Price", "InvoiceDate"])
    frame["line_revenue_gbp"] = frame["Quantity"] * frame["Price"]
    # Keep only genuine sale lines (positive quantity and price).
    frame = frame[(frame["Quantity"] > 0) & (frame["Price"] > 0)]
    frame["order_date"] = pd.to_datetime(frame["InvoiceDate"]).dt.normalize()
    frame["customer_id"] = "OR-" + frame["Customer ID"].astype(int).astype(str)

    grouped = frame.groupby("Invoice", as_index=False).agg(
        customer_id=("customer_id", "first"),
        order_date=("order_date", "min"),
        gross_revenue_gbp=("line_revenue_gbp", "sum"),
    )
    grouped = grouped[grouped["gross_revenue_gbp"] > 0]

    orders = pd.DataFrame(
        {
            "order_id": "ORD-" + grouped["Invoice"].astype(str),
            "customer_id": grouped["customer_id"],
            "order_date": grouped["order_date"],
            "gross_revenue_gbp": grouped["gross_revenue_gbp"].round(2),
            "discount_gbp": 0.0,
            "refund_gbp": 0.0,
            "shipping_revenue_gbp": 0.0,
            "gross_margin_gbp": (grouped["gross_revenue_gbp"] * gross_margin_rate).round(2),
            "order_status": "completed",
        }
    )
    return orders.sort_values(["order_date", "order_id"]).reset_index(drop=True)


def _build_customers(raw: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    country_lookup = _customer_country(raw)
    first_order = orders.groupby("customer_id", as_index=False)["order_date"].min()
    first_order = first_order.rename(columns={"order_date": "first_order_date"})

    snapshot_date = orders["order_date"].max()

    customers = first_order.copy()
    customers["acquisition_date"] = customers["first_order_date"]
    customers["acquisition_channel"] = customers["customer_id"].map(
        lambda cid: _stable_choice(f"channel:{cid}", CUSTOMER_CHANNELS)
    )
    customers["country"] = customers["customer_id"].map(country_lookup).fillna("Unknown")
    customers["email_opt_in"] = customers["customer_id"].map(
        lambda cid: int(_stable_bucket(f"email:{cid}") < 70)
    )
    customers["sms_opt_in"] = customers["customer_id"].map(
        lambda cid: int(_stable_bucket(f"sms:{cid}") < 40)
    )

    latest_order = orders.groupby("customer_id")["order_date"].max()
    lifecycle_recency = (snapshot_date - customers["customer_id"].map(latest_order)).dt.days
    customers["lifecycle_status"] = _lifecycle_from_recency(lifecycle_recency)

    return customers[
        [
            "customer_id",
            "acquisition_date",
            "first_order_date",
            "acquisition_channel",
            "country",
            "email_opt_in",
            "sms_opt_in",
            "lifecycle_status",
        ]
    ].reset_index(drop=True)


def _customer_country(raw: pd.DataFrame) -> dict[str, str]:
    frame = raw.loc[:, ["Customer ID", "Country"]].copy()
    frame["Customer ID"] = pd.to_numeric(frame["Customer ID"], errors="coerce")
    frame = frame.dropna(subset=["Customer ID"])
    frame["customer_id"] = "OR-" + frame["Customer ID"].astype(int).astype(str)
    # Most frequent country per customer.
    modal = frame.groupby("customer_id")["Country"].agg(
        lambda values: values.mode().iat[0] if not values.mode().empty else "Unknown"
    )
    return modal.to_dict()


def _lifecycle_from_recency(recency_days: pd.Series) -> pd.Series:
    bins = [-1, 30, 120, 240, 10**9]
    labels = list(LIFECYCLE_SEGMENTS)
    banded = pd.cut(recency_days.fillna(10**9), bins=bins, labels=labels)
    return banded.astype(str)


def _stable_bucket(value: str, modulo: int = 100) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulo


def _stable_choice(value: str, options: tuple[str, ...]) -> str:
    return options[_stable_bucket(value, len(options))]


__all__ = [
    "build_customer_tables_from_online_retail",
    "build_shopify_connector_from_online_retail",
    "dataset_provenance",
    "DEFAULT_GROSS_MARGIN_RATE",
]
