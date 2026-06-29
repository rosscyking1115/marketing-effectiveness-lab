"""Generate a one-page stakeholder business-impact brief (Markdown + PDF).

Runs the demo MMM and budget pipeline, derives a budget-neutral profit-maximising
reallocation, scores recommendation readiness, summarises customer economics, and
packages everything into a single-page brief via
``reporting.build_business_impact_summary``.

The Markdown brief needs no extra dependencies. The PDF is rendered with reportlab
(optional ``brief`` dependency group) by styling the same Markdown content, so both
artifacts share one source of truth.

Usage:

    uv run python scripts/build_stakeholder_brief.py            # Markdown only
    uv run --group brief python scripts/build_stakeholder_brief.py   # Markdown + PDF

Outputs are written to ``.local/stakeholder_brief/`` (git-ignored).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from marketing_effectiveness_lab.analytics import prepare_weekly_frame, summarize_kpis
from marketing_effectiveness_lab.budget import (
    current_weekly_spend,
    evaluate_budget_scenario,
    optimize_budget_allocation,
)
from marketing_effectiveness_lab.customer import (
    prepare_customer_tables,
    score_customer_lapse_value,
    summarize_customer_kpis,
)
from marketing_effectiveness_lab.data.customer_generator import generate_customer_demo_data
from marketing_effectiveness_lab.data.generator import generate_weekly_demo_data
from marketing_effectiveness_lab.governance import assess_recommendation_readiness
from marketing_effectiveness_lab.mmm import fit_mmm_foundation_model
from marketing_effectiveness_lab.reporting import (
    build_business_impact_summary,
    build_executive_summary,
    business_impact_markdown,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".local" / "stakeholder_brief"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the stakeholder business-impact brief.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _customer_highlights(seed: int) -> dict[str, object]:
    dataset = generate_customer_demo_data(seed=seed, customer_count=800)
    tables = prepare_customer_tables(dataset.as_tables())
    kpis = summarize_customer_kpis(tables["customers"], tables["orders"], tables["customer_segments"])
    scored = score_customer_lapse_value(
        tables["customers"],
        tables["orders"],
        as_of_date="2025-12-31",
        calibration_cutoff_date="2025-01-01",
        horizon_days=180,
    )
    return {
        "source_label": "Synthetic customer demo (swap in data/public for real)",
        "customers": int(kpis.total_customers),
        "repeat_purchase_rate": float(kpis.repeat_purchase_rate),
        "mean_expected_future_margin_gbp": float(scored["expected_future_margin_gbp"].mean()),
        "high_lapse_risk_customers": int((scored["lapse_risk_band"] == "High").sum()),
    }


def _build_summary(seed: int):
    df, _ = generate_weekly_demo_data(seed=seed)
    prepared = prepare_weekly_frame(df)
    kpis = summarize_kpis(prepared)
    mmm_result = fit_mmm_foundation_model(df, holdout_weeks=26)

    current = current_weekly_spend(df, lookback_weeks=13)
    # Budget-neutral, profit-maximising reallocation: same total spend, better mix.
    optimization = optimize_budget_allocation(
        current, mmm_result, total_budget_gbp=sum(current.values()), objective="profit"
    )
    scenario = evaluate_budget_scenario(df, mmm_result, optimization.allocation, lookback_weeks=13)
    executive_summary = build_executive_summary(kpis, mmm_result, scenario)
    readiness = assess_recommendation_readiness(
        mmm_result, scenario, weekly_rows=len(prepared), evidence_quality=None
    )
    return build_business_impact_summary(
        kpis,
        mmm_result,
        scenario,
        readiness,
        executive_summary,
        data_source_label="UK fashion ecommerce demo dataset",
        customer_highlights=_customer_highlights(seed),
    )


def _render_pdf(markdown_text: str, pdf_path: Path) -> bool:
    try:
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer
    except ModuleNotFoundError:
        return False

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, leading=13, alignment=TA_LEFT)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=3)
    title = ParagraphStyle("title", parent=styles["Title"], fontSize=18, spaceAfter=4)

    def _inline(text: str) -> str:
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        while "**" in text:
            text = text.replace("**", "<b>", 1).replace("**", "</b>", 1)
        if text.startswith("_") and text.endswith("_") and len(text) > 1:
            text = f"<i>{text[1:-1]}</i>"
        return text

    flow: list = []
    bullets: list = []

    def _flush_bullets() -> None:
        if bullets:
            flow.append(ListFlowable(list(bullets), bulletType="bullet", leftIndent=10))
            bullets.clear()

    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            _flush_bullets()
            flow.append(Paragraph(_inline(line[2:]), title))
        elif line.startswith("## "):
            _flush_bullets()
            flow.append(Paragraph(_inline(line[3:]), h2))
        elif line.startswith("- "):
            bullets.append(ListItem(Paragraph(_inline(line[2:]), body), leftIndent=10))
        elif line:
            _flush_bullets()
            flow.append(Paragraph(_inline(line), body))
        else:
            _flush_bullets()
            flow.append(Spacer(1, 4))

    _flush_bullets()
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
    )
    doc.build(flow)
    return True


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary = _build_summary(args.seed)
    markdown_text = business_impact_markdown(summary)

    md_path = args.output_dir / "business_impact_brief.md"
    md_path.write_text(markdown_text, encoding="utf-8")
    print(f"Wrote Markdown brief: {md_path}")

    pdf_path = args.output_dir / "business_impact_brief.pdf"
    if _render_pdf(markdown_text, pdf_path):
        print(f"Wrote PDF brief: {pdf_path}")
    else:
        print(
            "reportlab not installed; skipped PDF. "
            "Run with: uv run --group brief python scripts/build_stakeholder_brief.py"
        )


if __name__ == "__main__":
    main()
