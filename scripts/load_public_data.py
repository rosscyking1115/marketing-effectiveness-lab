"""Run the customer-analytics layer on a real, public dataset.

Downloads the UCI *Online Retail II* dataset (real UK online-retailer transactions,
2009-2011), maps it to the package's customer/order schema, validates it, runs the
cohort, value-window, CLV, and lapse-risk analytics on the real purchases, and writes
the mapped tables plus a provenance-documented Markdown summary to ``data/public/``.

Usage:

    uv run --group data python scripts/load_public_data.py
    uv run --group data python scripts/load_public_data.py --raw-path path/to/online_retail_II.xlsx

The raw download and all outputs live under ``data/public/`` which is git-ignored.
"""

from __future__ import annotations

import argparse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from marketing_effectiveness_lab.customer import (
    cohort_retention,
    customer_future_value_backtest,
    new_vs_returning_summary,
    score_customer_lapse_value,
)
from marketing_effectiveness_lab.data.customer_schema import validate_customer_table
from marketing_effectiveness_lab.data.online_retail import (
    DEFAULT_GROSS_MARGIN_RATE,
    build_customer_tables_from_online_retail,
    dataset_provenance,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "public"
DATASET_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run customer analytics on UCI Online Retail II.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--raw-path",
        type=Path,
        default=None,
        help="Path to a local online_retail_II.xlsx; downloaded if omitted.",
    )
    parser.add_argument("--gross-margin-rate", type=float, default=DEFAULT_GROSS_MARGIN_RATE)
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
        extracted = output_dir / names[0]
    extracted.replace(xlsx_path)
    zip_path.unlink(missing_ok=True)
    return xlsx_path


def _read_online_retail(xlsx_path: Path) -> pd.DataFrame:
    print(f"Reading {xlsx_path} ...")
    sheets = pd.read_excel(xlsx_path, sheet_name=None)
    return pd.concat(sheets.values(), ignore_index=True)


def _write_summary(
    output_dir: Path,
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    gross_margin_rate: float,
) -> Path:
    snapshot = orders["order_date"].max()
    cutoff = snapshot - pd.Timedelta(days=180)
    repeat = new_vs_returning_summary(customers, orders)
    retention = cohort_retention(customers, orders, max_month_number=12)
    backtest = customer_future_value_backtest(
        customers, orders, cutoff_date=cutoff, horizon_days=180
    )
    scored = score_customer_lapse_value(
        customers, orders, as_of_date=snapshot, calibration_cutoff_date=cutoff, horizon_days=180
    )

    month_curve = retention.groupby("month_number")["active_customers"].sum()
    base = float(month_curve.get(0, 0)) or 1.0
    provenance = dataset_provenance()

    lines = [
        "# Real Public Data Run - UCI Online Retail II",
        "",
        f"- Source: {provenance['source']}",
        f"- Source URL: {provenance['source_url']}",
        f"- Customers: {len(customers):,}",
        f"- Orders: {len(orders):,}",
        f"- Date range: {orders['order_date'].min().date()} to {snapshot.date()}",
        f"- Gross revenue (GBP): {orders['gross_revenue_gbp'].sum():,.0f}",
        f"- Repeat-customer order share: "
        f"{repeat.set_index('customer_order_type')['orders'].get('Returning customer orders', 0) / len(orders):.1%}",
        "",
        "## Cohort retention (share of acquisition-month buyers still active)",
        f"- Month 1: {float(month_curve.get(1, 0)) / base:.1%}",
        f"- Month 3: {float(month_curve.get(3, 0)) / base:.1%}",
        f"- Month 6: {float(month_curve.get(6, 0)) / base:.1%}",
        "",
        "## CLV / lapse baselines",
        f"- Mean expected 180-day future margin per customer (GBP): "
        f"{scored['expected_future_margin_gbp'].mean():,.2f}",
        f"- Backtest segments evaluated: {len(backtest)}",
        f"- High lapse-risk customers: {int((scored['lapse_risk_band'] == 'High').sum()):,}",
        "",
        "## Provenance",
        f"- Real fields: {', '.join(provenance['real_fields'])}",
        f"- Imputed overlays: {', '.join(provenance['imputed_fields'])}",
        f"- Gross margin rate assumed: {gross_margin_rate:.0%}",
        f"- Excluded rows: {provenance['excluded_rows']}",
        "",
        "_Margin, acquisition channel, and CRM opt-in are synthetic overlays; all cohort,"
        " repeat, value, and lapse signals above are computed from real transactions._",
        "",
    ]
    summary_path = output_dir / "real_data_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    xlsx_path = _ensure_raw_xlsx(args.output_dir, args.raw_path)
    raw = _read_online_retail(xlsx_path)
    tables = build_customer_tables_from_online_retail(raw, gross_margin_rate=args.gross_margin_rate)
    customers, orders = tables["customers"], tables["orders"]

    errors = validate_customer_table("customers", customers) + validate_customer_table("orders", orders)
    if errors:
        raise ValueError("Mapped tables failed schema validation:\n- " + "\n- ".join(errors))

    customers.to_csv(args.output_dir / "online_retail_customers.csv", index=False)
    orders.to_csv(args.output_dir / "online_retail_orders.csv", index=False)
    summary_path = _write_summary(args.output_dir, customers, orders, args.gross_margin_rate)

    print(f"Mapped {len(customers):,} customers and {len(orders):,} orders from real data.")
    print(f"Wrote tables and summary to {args.output_dir}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
