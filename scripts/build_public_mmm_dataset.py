"""Assemble a weekly MMM dataset from real public outcome data (UCI Online Retail II).

Derives a real weekly Shopify/ecommerce **outcome** connector from the Online Retail II
transactions, runs it through the connector assembly pipeline, and reports source
diagnostics. This validates the connector -> assembly -> diagnostics path on real data.

It does **not** validate MMM channel attribution: real, public, weekly spend-by-channel
data is not available, so the paid-media connectors are absent and the assembled media
spend is zero. The diagnostics make that gap explicit.

Usage:

    uv run --group data python scripts/build_public_mmm_dataset.py
    uv run --group data python scripts/build_public_mmm_dataset.py --raw-path path/to/online_retail_II.xlsx

Outputs are written to ``data/public/`` (git-ignored).
"""

from __future__ import annotations

import argparse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from marketing_effectiveness_lab.data.assembly import assemble_weekly_dataset_from_connectors
from marketing_effectiveness_lab.data.diagnostics import assembled_weekly_diagnostics
from marketing_effectiveness_lab.data.online_retail import (
    build_shopify_connector_from_online_retail,
    dataset_provenance,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "public"
DATASET_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble a weekly MMM dataset from Online Retail II.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--raw-path", type=Path, default=None)
    return parser.parse_args()


def _ensure_raw_xlsx(output_dir: Path, raw_path: Path | None) -> Path:
    if raw_path is not None:
        return raw_path
    output_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = output_dir / "online_retail_II.xlsx"
    if xlsx_path.exists():
        return xlsx_path
    zip_path = output_dir / "online_retail_II.zip"
    print(f"Downloading {DATASET_URL} ...")
    urllib.request.urlretrieve(DATASET_URL, zip_path)  # noqa: S310 - fixed, trusted UCI URL
    with zipfile.ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".xlsx")]
        if not names:
            raise RuntimeError("Downloaded archive did not contain an .xlsx file.")
        archive.extract(names[0], output_dir)
        (output_dir / names[0]).replace(xlsx_path)
    zip_path.unlink(missing_ok=True)
    return xlsx_path


def _write_summary(output_dir: Path, weekly: pd.DataFrame, diagnostics: pd.DataFrame, errors: list[str]) -> Path:
    provenance = dataset_provenance()
    week_start = pd.to_datetime(weekly["week_start"])
    lines = [
        "# Real Public MMM Dataset - assembled from UCI Online Retail II",
        "",
        f"- Source: {provenance['source']}",
        f"- Assembled weeks: {len(weekly):,}",
        f"- Week range: {week_start.min().date()} to {week_start.max().date()}",
        f"- Total net revenue (GBP): {weekly['revenue_gbp'].sum():,.0f}",
        f"- Total orders: {int(weekly['orders'].sum()):,}",
        f"- Mean weekly AOV (GBP): {weekly['average_order_value_gbp'].mean():,.2f}",
        "",
        "## Source diagnostics",
    ]
    lines += [f"- {row['check']}: {row['status']} - {row['detail']}" for row in diagnostics.to_dict("records")]
    lines += [
        "",
        "## Scope and honesty",
        "- Outcome (revenue, orders, returns, AOV) is REAL, derived from the transactions.",
        "- Paid-media spend connectors are absent: real, public weekly spend-by-channel data",
        "  does not exist, so media spend is zero and MMM channel attribution is NOT validated",
        "  on real spend. Supplying a real ad-platform export is the remaining step.",
    ]
    if errors:
        lines += ["", "## Final weekly-schema validation notes"]
        lines += [f"- {error}" for error in errors]
    lines.append("")
    summary_path = output_dir / "real_mmm_dataset_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def _read_online_retail(xlsx_path: Path) -> pd.DataFrame:
    print(f"Reading {xlsx_path} ...")
    sheets = pd.read_excel(xlsx_path, sheet_name=None)
    return pd.concat(sheets.values(), ignore_index=True)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw = _read_online_retail(_ensure_raw_xlsx(args.output_dir, args.raw_path))
    connector = build_shopify_connector_from_online_retail(raw)
    result = assemble_weekly_dataset_from_connectors({"shopify": connector})
    diagnostics = assembled_weekly_diagnostics(
        result.weekly_dataset, result.source_summary, result.validation_errors
    )

    connector.to_csv(args.output_dir / "online_retail_shopify_connector.csv", index=False)
    result.weekly_dataset.to_csv(args.output_dir / "online_retail_weekly_mmm.csv", index=False)
    diagnostics.to_csv(args.output_dir / "online_retail_source_diagnostics.csv", index=False)
    summary_path = _write_summary(
        args.output_dir, result.weekly_dataset, diagnostics, result.validation_errors
    )

    print(f"Assembled {len(result.weekly_dataset):,} weekly rows from real transactions.")
    print(f"Wrote outputs to {args.output_dir}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
