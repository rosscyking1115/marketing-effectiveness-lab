from __future__ import annotations

import pandas as pd

from marketing_effectiveness_lab.data.customer_generator import generate_customer_demo_data
from marketing_effectiveness_lab.data.customer_schema import (
    CUSTOMER_TABLES,
    validate_customer_dataset,
    validate_customer_table,
)


def test_generated_customer_demo_data_matches_schema() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)

    assert validate_customer_dataset(dataset.as_tables()) == []
    assert len(dataset.customers) == 800
    assert len(dataset.orders) >= len(dataset.customers)
    assert set(CUSTOMER_TABLES).issubset(dataset.as_tables())
    assert dataset.customer_segments["customer_id"].is_unique
    assert dataset.crm_events["campaign_id"].nunique() == len(dataset.crm_campaigns)


def test_customer_demo_data_has_commercial_signal() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=800)

    assert dataset.orders["gross_revenue_gbp"].sum() > 0
    assert dataset.orders["gross_margin_gbp"].sum() > 0
    assert dataset.returns["refund_gbp"].sum() > 0
    assert dataset.customer_segments["lifecycle_segment"].nunique() > 1
    assert dataset.customer_segments["value_segment"].nunique() == 4
    assert set(dataset.crm_events["treatment_group"]) == {"target", "holdout"}
    assert dataset.crm_events["converted_flag"].sum() > 0


def test_customer_schema_rejects_bad_flag_values() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=200)
    customers = dataset.customers.copy()
    customers.loc[0, "email_opt_in"] = 2

    errors = validate_customer_table("customers", customers)

    assert "customers: email_opt_in must contain only 0/1 values." in errors


def test_customer_dataset_rejects_broken_foreign_key() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=200)
    tables = dataset.as_tables()
    tables["orders"] = tables["orders"].copy()
    tables["orders"].loc[0, "customer_id"] = "CUST-DOES-NOT-EXIST"

    errors = validate_customer_dataset(tables)

    assert "orders: customer_id contains 1 value(s) not found in customers." in errors


def test_customer_schema_rejects_duplicate_keys() -> None:
    dataset = generate_customer_demo_data(seed=42, customer_count=200)
    duplicated_customers = pd.concat(
        [dataset.customers, dataset.customers.head(1)],
        ignore_index=True,
    )

    errors = validate_customer_table("customers", duplicated_customers)

    assert "customers: customer_id must be unique." in errors
