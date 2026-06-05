from __future__ import annotations

import pandas as pd

from marketing_effectiveness_lab.data.assembly import assemble_weekly_dataset_from_connectors
from marketing_effectiveness_lab.data.connectors import connector_template_dataframe
from marketing_effectiveness_lab.data.diagnostics import assembled_weekly_diagnostics


def test_diagnostics_pass_schema_and_review_short_history() -> None:
    result = assemble_weekly_dataset_from_connectors(
        {
            "ga4": connector_template_dataframe("ga4"),
            "google_ads": connector_template_dataframe("google_ads"),
            "meta_ads": connector_template_dataframe("meta_ads"),
            "shopify": connector_template_dataframe("shopify"),
            "crm": connector_template_dataframe("crm"),
        }
    )

    diagnostics = assembled_weekly_diagnostics(
        result.weekly_dataset,
        result.source_summary,
        result.validation_errors,
    )

    assert _status(diagnostics, "Weekly schema") == "Pass"
    assert _status(diagnostics, "Weekly history") == "Review"
    assert _status(diagnostics, "Media coverage") == "Pass"
    assert _status(diagnostics, "Organic search") == "Pass"


def test_diagnostics_block_empty_dataset() -> None:
    diagnostics = assembled_weekly_diagnostics(pd.DataFrame())

    assert _status(diagnostics, "Weekly dataset") == "Block"
    assert _status(diagnostics, "Source coverage") == "Review"


def test_diagnostics_surface_validation_errors() -> None:
    result = assemble_weekly_dataset_from_connectors({"shopify": connector_template_dataframe("shopify")})

    diagnostics = assembled_weekly_diagnostics(
        result.weekly_dataset,
        result.source_summary,
        ["week_start must be continuous weekly dates."],
    )

    assert _status(diagnostics, "Weekly schema") == "Block"
    assert "continuous weekly dates" in _detail(diagnostics, "Weekly schema")


def test_diagnostics_review_limited_media_and_missing_organic() -> None:
    result = assemble_weekly_dataset_from_connectors({"shopify": connector_template_dataframe("shopify")})

    diagnostics = assembled_weekly_diagnostics(result.weekly_dataset, result.source_summary)

    assert _status(diagnostics, "Media coverage") == "Block"
    assert _status(diagnostics, "Organic search") == "Review"
    assert _status(diagnostics, "Display connector") == "Info"


def test_diagnostics_review_customer_count_anomaly() -> None:
    result = assemble_weekly_dataset_from_connectors({"shopify": connector_template_dataframe("shopify")})
    weekly = result.weekly_dataset.copy()
    weekly.loc[0, "new_customers"] = weekly.loc[0, "orders"] + 1

    diagnostics = assembled_weekly_diagnostics(weekly, result.source_summary)

    assert _status(diagnostics, "Customer counts") == "Review"


def _status(diagnostics: pd.DataFrame, check: str) -> str:
    return str(diagnostics.loc[diagnostics["check"] == check, "status"].iloc[0])


def _detail(diagnostics: pd.DataFrame, check: str) -> str:
    return str(diagnostics.loc[diagnostics["check"] == check, "detail"].iloc[0])
