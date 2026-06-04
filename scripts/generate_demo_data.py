from __future__ import annotations

import argparse
from pathlib import Path

from marketing_effectiveness_lab.data.generator import generate_and_validate


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "demo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate demo data for Marketing Effectiveness Lab.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible data.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where generated data should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = generate_and_validate(args.output_dir, seed=args.seed)
    print(f"Generated {len(df):,} weekly rows in {args.output_dir}")
    print(f"Revenue range: GBP {df['revenue_gbp'].min():,.0f} to {df['revenue_gbp'].max():,.0f}")
    print(f"Total media spend: GBP {df.filter(like='_spend_gbp').sum().sum():,.0f}")


if __name__ == "__main__":
    main()

