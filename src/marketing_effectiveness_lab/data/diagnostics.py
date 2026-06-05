"""Quality diagnostics for assembled weekly marketing datasets."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from marketing_effectiveness_lab.analytics import CHANNEL_LABELS
from marketing_effectiveness_lab.data.schema import validate_weekly_dataset


ZERO_DEFAULT_CHANNELS = {
    "display_spend_gbp": "Display",
    "affiliates_spend_gbp": "Affiliates",
    "influencer_spend_gbp": "Influencer",
}


def assembled_weekly_diagnostics(
    weekly_dataset: pd.DataFrame,
    source_summary: pd.DataFrame | None = None,
    validation_errors: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return data-quality diagnostics for connector-assembled weekly data."""

    rows: list[dict[str, str]] = []
    validation_errors = list(validation_errors or [])

    if weekly_dataset.empty:
        rows.append(
            _row(
                "Weekly dataset",
                "Block",
                "No assembled weekly rows are available.",
            )
        )
        rows.extend(_source_coverage_rows(source_summary, expected_weeks=0))
        return pd.DataFrame(rows)

    weekly = weekly_dataset.copy()
    weekly["week_start"] = pd.to_datetime(weekly["week_start"], errors="coerce")
    expected_weeks = len(weekly)

    if validation_errors:
        rows.append(
            _row(
                "Weekly schema",
                "Block",
                "; ".join(validation_errors),
            )
        )
    else:
        schema_errors = validate_weekly_dataset(weekly_dataset)
        rows.append(
            _row(
                "Weekly schema",
                "Pass" if not schema_errors else "Block",
                "Final weekly dataset passes validation."
                if not schema_errors
                else "; ".join(schema_errors),
            )
        )

    rows.append(_history_row(weekly))
    rows.append(_outcome_row(weekly))
    rows.append(_customer_row(weekly))
    rows.append(_media_coverage_row(weekly))
    rows.append(_organic_row(weekly))
    rows.extend(_default_channel_rows(weekly))
    rows.extend(_source_coverage_rows(source_summary, expected_weeks=expected_weeks))

    return pd.DataFrame(rows, columns=["check", "status", "detail"])


def _history_row(weekly: pd.DataFrame) -> dict[str, str]:
    week_count = len(weekly)
    if week_count >= 104:
        status = "Pass"
        detail = f"{week_count} weekly rows support stronger MMM diagnostics."
    elif week_count >= 57:
        status = "Pass"
        detail = f"{week_count} weekly rows meet the current holdout workflow minimum."
    else:
        status = "Review"
        detail = f"{week_count} weekly rows assembled; current modeling views need at least 57."
    return _row("Weekly history", status, detail)


def _outcome_row(weekly: pd.DataFrame) -> dict[str, str]:
    bad_rows = weekly[(weekly["revenue_gbp"] <= 0) | (weekly["orders"] <= 0)]
    if bad_rows.empty:
        return _row("Outcome quality", "Pass", "Revenue and orders are positive for every week.")
    return _row(
        "Outcome quality",
        "Block",
        f"{len(bad_rows)} weeks have non-positive revenue or orders.",
    )


def _customer_row(weekly: pd.DataFrame) -> dict[str, str]:
    bad_rows = weekly[weekly["new_customers"] > weekly["orders"]]
    if bad_rows.empty:
        return _row("Customer counts", "Pass", "New-customer orders do not exceed total orders.")
    return _row(
        "Customer counts",
        "Review",
        f"{len(bad_rows)} weeks have new customers above total orders.",
    )


def _media_coverage_row(weekly: pd.DataFrame) -> dict[str, str]:
    spend_columns = [column for column in CHANNEL_LABELS if column in weekly.columns]
    active_channels = [column for column in spend_columns if weekly[column].sum() > 0]
    if len(active_channels) >= 3:
        status = "Pass"
    elif len(active_channels) >= 1:
        status = "Review"
    else:
        status = "Block"

    labels = [CHANNEL_LABELS[column] for column in active_channels]
    detail = (
        f"{len(active_channels)} active paid/owned spend channels: {', '.join(labels)}."
        if labels
        else "No non-zero media spend channels were assembled."
    )
    return _row("Media coverage", status, detail)


def _organic_row(weekly: pd.DataFrame) -> dict[str, str]:
    if "organic_search_sessions" not in weekly:
        return _row("Organic search", "Review", "Organic search sessions are missing.")
    if weekly["organic_search_sessions"].sum() <= 0:
        return _row(
            "Organic search",
            "Review",
            "Organic search sessions are all zero; GA4 organic source rows may be missing.",
        )
    return _row("Organic search", "Pass", "Organic search sessions are available.")


def _default_channel_rows(weekly: pd.DataFrame) -> list[dict[str, str]]:
    rows = []
    for column, label in ZERO_DEFAULT_CHANNELS.items():
        if column in weekly and weekly[column].sum() == 0:
            rows.append(
                _row(
                    f"{label} connector",
                    "Info",
                    f"{label} spend is currently defaulted to zero until a source connector is added.",
                )
            )
    return rows


def _source_coverage_rows(
    source_summary: pd.DataFrame | None,
    expected_weeks: int,
) -> list[dict[str, str]]:
    if source_summary is None or source_summary.empty:
        return [_row("Source coverage", "Review", "No connector source summary is available.")]

    rows = []
    for source in source_summary.to_dict("records"):
        weeks = int(source["weeks"])
        connector = str(source["connector"])
        if expected_weeks and weeks < expected_weeks:
            status = "Review"
            detail = f"{connector} covers {weeks} of {expected_weeks} assembled weeks."
        else:
            status = "Pass"
            detail = f"{connector} covers {weeks} weekly periods."
        rows.append(_row("Source coverage", status, detail))
    return rows


def _row(check: str, status: str, detail: str) -> dict[str, str]:
    return {"check": check, "status": status, "detail": detail}
