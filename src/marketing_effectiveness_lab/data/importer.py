"""CSV import helpers for real-data-ready workflows."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import BinaryIO, TextIO

import pandas as pd

from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.data.schema import REQUIRED_COLUMNS, validate_weekly_dataset


def template_dataframe(rows: int = 8) -> pd.DataFrame:
    """Return a small schema-compliant template populated with demo-style values."""

    demo_df, _ = generate_weekly_demo_data(seed=7)
    columns = [column.name for column in REQUIRED_COLUMNS]
    return demo_df[columns].head(rows).copy()


def template_csv(rows: int = 8) -> str:
    """Return a CSV template that can be downloaded from the app."""

    return template_dataframe(rows=rows).to_csv(index=False)


def load_weekly_csv(source: str | Path | BinaryIO | TextIO) -> pd.DataFrame:
    """Load and validate a weekly marketing CSV from a path or file-like object."""

    df = pd.read_csv(source)
    errors = validate_weekly_dataset(df)
    if errors:
        raise ValueError("Dataset validation failed:\n- " + "\n- ".join(errors))
    return _coerce_weekly_types(df)


def validate_csv_text(csv_text: str) -> tuple[pd.DataFrame | None, list[str]]:
    """Validate CSV text and return either a typed frame or validation errors."""

    try:
        df = pd.read_csv(StringIO(csv_text))
    except Exception as exc:  # pragma: no cover - exact parser errors vary by pandas version.
        return None, [f"CSV could not be parsed: {exc}"]

    errors = validate_weekly_dataset(df)
    if errors:
        return None, errors
    return _coerce_weekly_types(df), []


def _coerce_weekly_types(df: pd.DataFrame) -> pd.DataFrame:
    typed = df.copy()
    typed["week_start"] = pd.to_datetime(typed["week_start"]).dt.strftime("%Y-%m-%d")
    for column in typed.columns:
        if column == "week_start":
            continue
        typed[column] = pd.to_numeric(typed[column])
    return typed

