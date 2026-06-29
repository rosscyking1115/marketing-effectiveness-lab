from __future__ import annotations

import pandas as pd

from marketing_effectiveness_lab.customer import (
    cohort_retention,
    customer_value_windows,
)
from marketing_effectiveness_lab.data.customer_schema import (
    CUSTOMER_CHANNELS,
    LIFECYCLE_SEGMENTS,
    validate_customer_table,
)
from marketing_effectiveness_lab.data.online_retail import (
    build_customer_tables_from_online_retail,
    dataset_provenance,
)


def _raw_fixture() -> pd.DataFrame:
    # Columns mirror the UCI Online Retail II export. Rows cover: a multi-line
    # invoice, a repeat order, a second customer, a cancellation (C-invoice), a
    # row with no customer id, and a non-positive sale line -- the last three are
    # expected to be filtered out.
    uk = "United Kingdom"
    rows = [
        ("536365", "X", 6, "2010-12-01 08:26", 2.55, 17850, uk),
        ("536365", "Y", 2, "2010-12-01 08:26", 3.39, 17850, uk),
        ("536400", "Z", 4, "2011-03-15 10:00", 5.00, 17850, uk),
        ("536500", "X", 10, "2011-06-20 12:00", 1.50, 12583, "France"),
        ("C536600", "X", -6, "2011-07-01 09:00", 2.55, 17850, uk),
        ("536700", "X", 3, "2011-08-01 09:00", 2.00, None, uk),
        ("536800", "BAD", -1, "2011-09-01 09:00", 2.00, 12583, "France"),
    ]
    columns = ["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
    return pd.DataFrame(rows, columns=columns)


def test_online_retail_adapter_maps_real_transactions_to_schema() -> None:
    tables = build_customer_tables_from_online_retail(_raw_fixture(), gross_margin_rate=0.45)
    customers = tables["customers"]
    orders = tables["orders"]

    # Cancellations, missing-customer rows, and non-positive lines are excluded.
    assert len(orders) == 3
    assert len(customers) == 2

    # Per-invoice revenue is the sum of its line items; margin uses the rate.
    first_order = orders.set_index("order_id").loc["ORD-536365"]
    assert first_order["gross_revenue_gbp"] == round(6 * 2.55 + 2 * 3.39, 2)
    assert first_order["gross_margin_gbp"] == round((6 * 2.55 + 2 * 3.39) * 0.45, 2)

    # The mapped tables satisfy the package schema.
    assert validate_customer_table("customers", customers) == []
    assert validate_customer_table("orders", orders) == []

    # Referential integrity: every order belongs to a known customer.
    assert set(orders["customer_id"]).issubset(set(customers["customer_id"]))

    # Overlays land in their allowed domains.
    assert set(customers["acquisition_channel"]).issubset(set(CUSTOMER_CHANNELS))
    assert set(customers["lifecycle_status"]).issubset(set(LIFECYCLE_SEGMENTS))


def test_online_retail_adapter_is_deterministic() -> None:
    raw = _raw_fixture()
    first = build_customer_tables_from_online_retail(raw)
    second = build_customer_tables_from_online_retail(raw)

    assert first["customers"].equals(second["customers"])
    assert first["orders"].equals(second["orders"])


def test_real_customer_analytics_run_on_mapped_tables() -> None:
    tables = build_customer_tables_from_online_retail(_raw_fixture())
    customers, orders = tables["customers"], tables["orders"]

    retention = cohort_retention(customers, orders, max_month_number=12)
    values = customer_value_windows(customers, orders)

    assert not retention.empty
    assert retention["month_number"].min() == 0
    # The repeat buyer (17850) shows activity beyond their acquisition month.
    assert (retention["month_number"] > 0).any()
    assert len(values) == len(customers)
    assert values["gross_margin_180d_gbp"].ge(0).all()


def test_dataset_provenance_documents_real_and_imputed_fields() -> None:
    provenance = dataset_provenance()

    assert "Online Retail II" in str(provenance["source"])
    assert "gross_margin_gbp" in provenance["imputed_fields"]
    assert any("order_date" in field for field in provenance["real_fields"])
