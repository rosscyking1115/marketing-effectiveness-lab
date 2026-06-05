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
        for connector_key in [
            "ga4",
            "google_ads",
            "meta_ads",
            "shopify",
            "crm",
            "display_ads",
            "affiliates",
            "influencer",
            "external_controls",
        ]
    }

    result = assemble_connector_csv_texts(csv_texts)

    assert result.validation_errors == []
    assert list(result.weekly_dataset.columns) == [column.name for column in REQUIRED_COLUMNS]
    assert len(result.weekly_dataset) == 2
    assert result.weekly_dataset["paid_search_spend_gbp"].sum() == 73_000
    assert result.weekly_dataset["paid_social_spend_gbp"].sum() == 73_000
    assert result.weekly_dataset["email_spend_gbp"].sum() == 5_700
    assert result.weekly_dataset["display_spend_gbp"].sum() == 30_700
    assert result.weekly_dataset["affiliates_spend_gbp"].sum() == 9_750
    assert result.weekly_dataset["influencer_spend_gbp"].sum() == 27_600
    assert result.weekly_dataset["organic_search_sessions"].sum() == 145_000
    assert result.weekly_dataset["consumer_confidence_index"].tolist() == [-18.0, -17.5]
    assert result.weekly_dataset["inflation_rate_pct"].tolist() == [3.9, 3.8]
    assert set(result.source_summary["connector"]) == {
        "GA4 traffic and conversion export",
        "Google Ads weekly export",
        "Meta Ads weekly export",
        "Shopify or ecommerce orders export",
        "CRM and lifecycle export",
        "Display ads weekly export",
        "Affiliate network weekly export",
        "Influencer weekly export",
        "External controls weekly export",
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


def test_assembly_maps_optional_channel_and_control_connectors() -> None:
    result = assemble_weekly_dataset_from_connectors(
        {
            "shopify": connector_template_dataframe("shopify"),
            "display_ads": connector_template_dataframe("display_ads"),
            "affiliates": connector_template_dataframe("affiliates"),
            "influencer": connector_template_dataframe("influencer"),
            "external_controls": connector_template_dataframe("external_controls"),
        }
    )

    assert result.validation_errors == []
    assert result.weekly_dataset["display_spend_gbp"].tolist() == [16_500, 14_200]
    assert result.weekly_dataset["affiliates_spend_gbp"].tolist() == [5_770, 3_980]
    assert result.weekly_dataset["influencer_spend_gbp"].tolist() == [15_000, 12_600]
    assert result.weekly_dataset["consumer_confidence_index"].tolist() == [-18.0, -17.5]
    assert result.weekly_dataset["inflation_rate_pct"].tolist() == [3.9, 3.8]
