from __future__ import annotations

import pandas as pd

from marketing_effectiveness_lab.data.assembly import (
    assemble_connector_csv_texts,
    assemble_weekly_dataset_from_connectors,
)
from marketing_effectiveness_lab.data.connectors import (
    connector_template_csv,
    connector_template_dataframe,
)
from marketing_effectiveness_lab.data.schema import REQUIRED_COLUMNS


def test_connector_templates_assemble_to_weekly_schema() -> None:
    csv_texts = {
        connector_key: connector_template_csv(connector_key)
        for connector_key in ["ga4", "google_ads", "meta_ads", "shopify", "crm"]
    }

    result = assemble_connector_csv_texts(csv_texts)

    assert result.validation_errors == []
    assert list(result.weekly_dataset.columns) == [column.name for column in REQUIRED_COLUMNS]
    assert len(result.weekly_dataset) == 2
    assert result.weekly_dataset["paid_search_spend_gbp"].sum() == 73_000
    assert result.weekly_dataset["paid_social_spend_gbp"].sum() == 73_000
    assert result.weekly_dataset["email_spend_gbp"].sum() == 5_700
    assert result.weekly_dataset["organic_search_sessions"].sum() == 145_000
    assert set(result.source_summary["connector"]) == {
        "GA4 traffic and conversion export",
        "Google Ads weekly export",
        "Meta Ads weekly export",
        "Shopify or ecommerce orders export",
        "CRM and lifecycle export",
    }


def test_shopify_export_is_reconciled_outcome_source() -> None:
    shopify = connector_template_dataframe("shopify")

    result = assemble_weekly_dataset_from_connectors({"shopify": shopify})

    assert result.validation_errors == []
    assert result.weekly_dataset["revenue_gbp"].tolist() == [1_055_000, 1_010_000]
    assert result.weekly_dataset["orders"].tolist() == [12_600, 11_900]
    assert result.weekly_dataset["new_customers"].tolist() == [5_400, 5_000]
    assert result.weekly_dataset["average_order_value_gbp"].round(1).tolist() == [83.7, 84.9]
    assert result.weekly_dataset["paid_search_spend_gbp"].sum() == 0


def test_assembly_requires_shopify_or_ecommerce_outcome() -> None:
    google_ads = connector_template_dataframe("google_ads")

    result = assemble_weekly_dataset_from_connectors({"google_ads": google_ads})

    assert result.weekly_dataset.empty
    assert result.validation_errors == [
        "Shopify or ecommerce orders export is required as the reconciled outcome source."
    ]


def test_assembly_reports_connector_validation_errors() -> None:
    shopify = connector_template_dataframe("shopify")
    shopify.loc[0, "net_sales_gbp"] = -1

    result = assemble_weekly_dataset_from_connectors({"shopify": shopify})

    assert result.weekly_dataset.empty
    assert (
        "Shopify or ecommerce orders export: net_sales_gbp contains negative values."
        in result.validation_errors
    )


def test_assembly_reports_final_weekly_schema_errors() -> None:
    shopify = connector_template_dataframe("shopify")
    shopify.loc[1, "week_start"] = "2025-01-27"

    result = assemble_weekly_dataset_from_connectors({"shopify": shopify})

    assert not result.weekly_dataset.empty
    assert "week_start must be continuous weekly dates." in result.validation_errors


def test_assembly_accepts_raw_numeric_strings() -> None:
    shopify = connector_template_dataframe("shopify").astype(str)

    result = assemble_weekly_dataset_from_connectors({"shopify": shopify})

    assert result.validation_errors == []
    assert pd.api.types.is_numeric_dtype(result.weekly_dataset["revenue_gbp"])
