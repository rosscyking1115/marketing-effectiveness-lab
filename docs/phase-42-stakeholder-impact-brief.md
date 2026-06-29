# Phase 42 - Stakeholder business-impact brief

Analysts already had a detailed model-run report and executive summary. This phase adds
a single-page, **stakeholder-facing business-impact brief** that rolls the analysis up
into the decision and its money impact, and renders it to PDF.

## What it produces

`reporting.build_business_impact_summary` aggregates existing outputs - KPIs, MMM
holdout accuracy, the recommended budget reallocation and its weekly/annualised profit
impact, recommendation readiness, optional customer/CLV highlights, and caveats - into a
`BusinessImpactSummary`. `reporting.business_impact_markdown` renders it as a
dependency-free one-page Markdown brief.

`scripts/build_stakeholder_brief.py` runs the demo pipeline end to end (MMM fit, a
budget-neutral profit-maximising reallocation, readiness, executive summary, and a
customer-economics roll-up), writes the Markdown brief, and renders a styled PDF.

```powershell
# Markdown only (no extra dependencies)
uv run python scripts/build_stakeholder_brief.py

# Markdown + PDF (reportlab)
uv run --group brief python scripts/build_stakeholder_brief.py
```

Outputs are written to `.local/stakeholder_brief/` (git-ignored).

## Design notes

- **One source of truth.** The PDF is a styled rendering of the same Markdown brief, so
  the two artifacts cannot drift apart.
- **PDF is optional.** `reportlab` lives in the `brief` dependency group; the package and
  test suite do not depend on it, and the Markdown brief works without it.
- **Honest defaults.** Scenario deltas default to "no change" when absent, but model
  metrics are required - a missing metric raises rather than printing a false zero (for
  example a misleading 0% MAPE). The customer section is omitted entirely when no
  highlights are supplied.
- **Real data.** The brief's customer section uses the synthetic customer demo by default;
  point it at the real Online Retail II outputs (see `phase-41-real-public-data.md`) to
  populate it from genuine purchase behaviour.
