from __future__ import annotations

from io import StringIO

import pandas as pd
import pytest

from marketing_effectiveness_lab.data.connectors import (
    CONNECTOR_SPECS,
    connector_catalog,
    connector_template_csv,
    connector_template_dataframe,
    validate_connector_csv_text,
)


def test_connector_catalog_lists_available_templates() -> None:
    catalog = connector_catalog()

    assert {"ga4", "google_ads", "meta_ads", "shopify", "crm"} == set(catalog["key"])
    assert catalog["required_columns"].min() > 0


def test_connector_templates_validate() -> None:
    for spec in CONNECTOR_SPECS:
        csv_text = connector_template_csv(spec.key)

        parsed, errors = validate_connector_csv_text(spec.key, csv_text)

        assert errors == []
        assert parsed is not None
        assert len(parsed) == len(spec.sample_rows)


def test_connector_template_csv_has_expected_columns() -> None:
    template = connector_template_dataframe("meta_ads")

    assert list(template.columns) == [
        "week_start",
        "campaign_name",
        "objective",
        "spend_gbp",
        "reach",
        "impressions",
        "link_clicks",
        "purchases",
        "purchase_value_gbp",
    ]


def test_connector_validation_reports_missing_columns() -> None:
    parsed, errors = validate_connector_csv_text("google_ads", "week_start,cost_gbp\n2025-01-06,1\n")

    assert parsed is None
    assert errors
    assert errors[0].startswith("Missing required columns")


def test_connector_validation_rejects_bad_dates_and_negative_values() -> None:
    template = pd.read_csv(StringIO(connector_template_csv("shopify")))
    template.loc[0, "week_start"] = "2025-01-07"
    template.loc[0, "gross_sales_gbp"] = -1

    parsed, errors = validate_connector_csv_text("shopify", template.to_csv(index=False))

    assert parsed is None
    assert "week_start must contain Monday week-start dates." in errors
    assert "gross_sales_gbp contains negative values." in errors


def test_unknown_connector_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown connector"):
        connector_template_dataframe("unknown")
