from __future__ import annotations

from io import StringIO

import pandas as pd

from marketing_effectiveness_lab.data.importer import (
    load_weekly_csv,
    template_csv,
    validate_csv_text,
)
from marketing_effectiveness_lab.data.schema import validate_weekly_dataset


def test_template_csv_loads_as_valid_weekly_dataset() -> None:
    csv_text = template_csv(rows=6)

    df = load_weekly_csv(StringIO(csv_text))

    assert len(df) == 6
    assert validate_weekly_dataset(df) == []


def test_validate_csv_text_returns_errors_for_missing_columns() -> None:
    df, errors = validate_csv_text("week_start,revenue_gbp\n2024-01-01,100\n")

    assert df is None
    assert errors
    assert errors[0].startswith("Missing required columns")


def test_validate_csv_text_returns_errors_for_non_numeric_values() -> None:
    template_df = pd.read_csv(StringIO(template_csv(rows=4)))
    template_df["orders"] = template_df["orders"].astype(object)
    template_df.loc[0, "orders"] = "not-a-number"
    csv_text = template_df.to_csv(index=False)

    df, errors = validate_csv_text(csv_text)

    assert df is None
    assert "orders contains non-numeric values." in errors


def test_load_weekly_csv_raises_for_invalid_data() -> None:
    csv_text = template_csv(rows=4).replace("2023-01-09", "2023-01-10")

    try:
        load_weekly_csv(StringIO(csv_text))
    except ValueError as exc:
        assert "week_start must contain Monday week-start dates." in str(exc)
    else:
        raise AssertionError("Expected invalid CSV to raise ValueError.")
