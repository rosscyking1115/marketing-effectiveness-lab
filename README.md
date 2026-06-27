# Marketing Effectiveness Lab

A portfolio-ready marketing effectiveness platform for a UK fashion ecommerce scenario, covering analytics, econometrics, MMM, incrementality evidence, connector data quality, and budget optimization.

The project is built to show the workflow expected from a commercial or marketing data scientist: define a business measurement problem, validate the data contract, model channel impact, quantify uncertainty, calibrate with experiments, and translate outputs into budget decisions.

## Live Project

- Portfolio site: <https://rosscyking1115.github.io/marketing-effectiveness-lab/>
- Interactive dashboard: <https://marketing-effectiveness-lab.streamlit.app/>
- GitHub repo: <https://github.com/rosscyking1115/marketing-effectiveness-lab>

## Reviewer Guide

For a quick portfolio review:

1. Open the portfolio site for the business framing and project narrative.
2. Open the Streamlit dashboard and review the analyst KPIs, MMM diagnostics, experiment calibration, Bayesian intervals, and budget planner.
3. Read the designed case-study pages:
   - Case study: <https://rosscyking1115.github.io/marketing-effectiveness-lab/case-study.html>
   - Architecture: <https://rosscyking1115.github.io/marketing-effectiveness-lab/architecture.html>
   - Data contract: <https://rosscyking1115.github.io/marketing-effectiveness-lab/data-contract.html>
4. Inspect the reusable package code in `src/marketing_effectiveness_lab/` and the test suite in `tests/`.

The strongest signal is not a single model output. It is the end-to-end workflow: data contract,
source validation, model diagnostics, incrementality evidence, uncertainty, optimization, and
stakeholder communication.

## What It Demonstrates

- Data contracts for weekly marketing, ecommerce, web analytics, paid media, CRM, affiliate, influencer, display, and external-control exports
- Synthetic customer, order, return, CRM campaign, and segment data contracts for customer growth analytics
- Connector assembly from validated source exports into an MMM-ready weekly dataset
- Source diagnostics for coverage, missing channels, outcome quality, and modeling readiness
- Analyst dashboarding for revenue, spend, promotions, channel mix, and correlations
- Customer and cohort intelligence for acquisition quality, lifecycle segments, and repeat behaviour
- Empirical CLV and lapse-risk baselines using customer margin, value windows, and segment backtests
- CRM incrementality diagnostics using campaign target/holdout events and profit-aware readouts
- Retention action planning that links lapse risk, expected margin, CRM evidence, holdouts, and incentive caps
- CRM experiment design for selected retention segments with sample-size guidance and launch guardrails
- Downloadable CRM experiment briefs and JSON artifacts for lightweight stakeholder review
- CRM experiment artifact comparison for prioritising saved retention tests
- CRM experiment portfolio planning for audience, holdout, and expected-margin trade-offs
- CRM portfolio eligibility checks for duplicate segments, targeting overlap, and launch guardrails
- Deterministic CRM audience assignment exports for treatment and holdout launch files
- Mutually exclusive CRM portfolio audience exports using rank-based assignment priority
- Baseline econometrics with time-aware holdout validation
- MMM-style adstock, saturation, contribution, ROI, and response curves
- Uncertainty intervals and a lightweight Bayesian posterior layer
- Lift-test evidence upload, governance, calibration, and experiment-informed priors
- Profit-aware scenario planning and constrained budget optimization
- Executive summary generation with stakeholder caveats
- Recommendation readiness scoring for stakeholder review governance
- Machine-readable model-run manifest for reproducibility and future artifact tracking
- Model-run manifest comparison for scenario review and artifact governance
- Customer/CRM data foundation for future cohort, lifecycle, CLV, and CRM incrementality workflows
- Customer cohort analytics for new vs returning economics and segment margin quality
- Explainable customer value and lapse-risk diagnostics for retention planning
- Target-vs-holdout CRM lift testing with incremental margin, cost, and evidence status
- Segment-level CRM retention recommendations for scale, holdout testing, retesting, suppression, and monitoring
- Launch-ready CRM holdout test briefs with audience split, success metric, guardrails, and checklist
- Deterministic CRM experiment artifacts for review, storage, and future comparison workflows
- Ranked CRM artifact comparison for readiness, value, audience, and holdout trade-offs
- CRM experiment portfolio summaries for multi-test launch planning
- CRM portfolio overlap and eligibility checks before launch
- Customer-level CRM treatment and holdout assignment exports
- Portfolio-level CRM audience exports with overlap suppression

The current version is polished for portfolio use and intentionally transparent about assumptions. The next product expansion would move from CSV contracts toward production-grade connector authentication, governed storage, model-run tracking, and role-based review workflows.

## Project Shape

- `docs/` - project briefs, data dictionary, methodology notes
- `src/marketing_effectiveness_lab/` - reusable Python package code
- `scripts/` - runnable project scripts
- `data/demo/` - generated demo data
- `SECURITY.md` - public demo data policy and production security notes
- `LICENSE` - MIT license for reuse and review

Useful docs:

- `docs/case-study.html` - designed business case study page
- `docs/architecture.html` - designed current and future architecture page
- `docs/data-contract.html` - designed data contract page
- `docs/case-study.md` - repo-native case study notes
- `docs/architecture.md` - repo-native architecture notes
- `docs/production-security-roadmap.md` - security and production roadmap
- `docs/data-dictionary.md` - weekly schema, connector templates, and assembly mapping
- `docs/phase-10-incrementality-calibration.md` - lift-test calibration workflow
- `docs/phase-11-experiment-evidence-upload.md` - real-data-ready experiment evidence upload
- `docs/phase-12-evidence-governance.md` - lift-test quality review and approval filtering
- `docs/phase-13-profit-aware-planning.md` - margin-aware budget scenario planning
- `docs/phase-14-bayesian-mmm-foundations.md` - Bayesian posterior layer and experiment-informed priors
- `docs/phase-15-constrained-budget-optimization.md` - constrained profit and contribution allocation
- `docs/phase-16-real-data-connectors.md` - connector templates for common marketing and commerce exports
- `docs/phase-17-weekly-assembly-pipeline.md` - assembly pipeline from connector exports to the weekly MMM schema
- `docs/phase-18-source-diagnostics.md` - source coverage and data-quality diagnostics for assembled connector data
- `docs/phase-19-expanded-connectors.md` - display, affiliate, influencer, and external-control connector coverage
- `docs/phase-20-model-run-reporting.md` - downloadable model-run report for review workflows
- `docs/phase-21-recommendation-readiness.md` - recommendation readiness gates for budget decisions
- `docs/phase-22-run-manifest.md` - machine-readable model-run manifest for reproducibility
- `docs/phase-23-manifest-comparison.md` - scenario comparison workflow for saved run manifests
- `docs/phase-24-customer-data-model.md` - customer/order/CRM data foundation for growth analytics
- `docs/phase-25-customer-cohort-intelligence.md` - customer cohort and lifecycle analytics
- `docs/phase-26-empirical-clv-lapse-risk.md` - empirical CLV and lapse-risk baseline methodology
- `docs/phase-27-crm-incrementality.md` - target/holdout CRM incrementality diagnostics
- `docs/phase-28-retention-action-planner.md` - retention segment action planning
- `docs/phase-29-crm-experiment-design.md` - CRM holdout experiment design and launch checks
- `docs/phase-30-crm-experiment-brief-export.md` - downloadable CRM experiment briefs and artifacts
- `docs/phase-31-crm-experiment-artifact-comparison.md` - comparison workflow for saved CRM experiment artifacts
- `docs/phase-32-crm-experiment-portfolio-planning.md` - portfolio planning for ranked CRM experiments
- `docs/phase-33-crm-portfolio-eligibility.md` - portfolio overlap and eligibility guardrails
- `docs/phase-34-crm-audience-assignment-export.md` - deterministic CRM audience assignment exports
- `docs/phase-35-crm-portfolio-audience-export.md` - mutually exclusive portfolio audience exports

## Quick Start

Generate the demo dataset:

```powershell
uv run python scripts/generate_demo_data.py
```

The generated files are written to `data/demo/`.

Launch the analyst dashboard:

```powershell
uv run streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
```

The repository also includes a root Streamlit Cloud entrypoint:

```powershell
uv run streamlit run streamlit_app.py
```

Run the test suite:

```powershell
uv run --group dev pytest
```

Run lint checks:

```powershell
uv run --group dev ruff check .
```

## Deployment

Live Streamlit app:

- <https://marketing-effectiveness-lab.streamlit.app/>

Streamlit Community Cloud settings:

- Repository: `rosscyking1115/marketing-effectiveness-lab`
- Branch: `main`
- Main file path: `streamlit_app.py`
- App URL: `marketing-effectiveness-lab`

GitHub Pages can host the static portfolio site from the `/docs` folder. Use it as the case-study website and link visitors to the Streamlit app for the interactive experience.

## Positioning

This project is aimed at the broad commercial data science lane:

- Marketing Data Scientist
- Commercial Data Scientist
- Product/Growth Analyst
- Marketing Analytics Consultant
- Retail/Fashion Data Scientist
