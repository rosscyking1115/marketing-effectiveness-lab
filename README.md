# Marketing Effectiveness Lab

An open, transparent workbench for marketing measurement: marketing mix modeling (MMM),
incrementality evidence, CRM experimentation, connector data quality, and profit-aware
budget decisions — built as a reusable Python package with a Streamlit dashboard.

> [!NOTE]
> This is a working prototype for learning, portfolio review, and workflow design. It runs
> on deterministic demo data and real *public* datasets — it is **not** yet a production
> system for confidential company data (authentication and governed storage are the named
> next phase). Boundaries are documented rather than hidden.

- **Product site:** <https://rosscyking1115.github.io/marketing-effectiveness-lab/>
- **Live dashboard:** <https://marketing-effectiveness-lab.streamlit.app/>

The point of the project is not a single model number — it is the **end-to-end workflow**:
data contract → source validation → diagnostics → modeling → incrementality evidence →
uncertainty → budget optimization → stakeholder communication → governance.

## What it does

**Data onboarding**
- Versioned data contracts and connector templates for ecommerce, web analytics, paid
  media, CRM, affiliate, influencer, display, and external-control exports.
- Connector assembly into an MMM-ready weekly dataset, with source-coverage and
  data-quality diagnostics.

**Measurement & modeling**
- Baseline econometrics with time-aware holdout validation.
- MMM-style adstock, saturation, contribution, ROI, and response curves.
- Uncertainty intervals and a lightweight Bayesian posterior layer.
- Lift-test evidence upload, quality governance, and experiment-informed calibration.

**Decisions**
- Profit-aware scenario planning and constrained budget optimization.
- Recommendation-readiness gates, executive summaries, and a one-page stakeholder
  business-impact brief (Markdown + PDF).

**Customer & CRM growth**
- Cohort, CLV, and lapse-risk analytics; target/holdout CRM incrementality with
  confidence intervals.
- Retention action planning and an end-to-end CRM experiment workflow: design, audience
  assignment, launch calendar, post-launch readouts, and a reusable learning library.

**Governance & reproducibility**
- Machine-readable model-run manifests, a local artifact registry, and a manifest
  comparison workflow.
- An access-governance demonstration: role-based permissions, an approval workflow with
  separation of duties, and a tamper-evident (hash-chained) audit log.

## Tech stack

| Area | Tools |
| --- | --- |
| Language | Python ≥ 3.11 |
| Data & modeling | pandas, NumPy, statsmodels |
| App & charts | Streamlit, Plotly |
| Tooling | uv (env & lockfile), pytest, ruff |
| Optional groups | `data` (openpyxl, for real public data), `brief` (reportlab, for the PDF brief) |

## Quick start

Prerequisite: [uv](https://docs.astral.sh/uv/).

```powershell
# Generate the deterministic demo dataset (written to data/demo/)
uv run python scripts/generate_demo_data.py

# Launch the analyst dashboard
uv run streamlit run app/streamlit_app.py --server.port 8501 --server.headless true

# Tests and lint
uv run --group dev pytest
uv run --group dev ruff check .
```

The repository also includes a root `streamlit_app.py` entrypoint used by Streamlit Cloud.

## Working with real public data

The pipeline runs on the real **UCI Online Retail II** dataset (a UK online retailer), not
only synthetic data.

```powershell
# Customer / cohort / CLV analytics on real transactions
uv run --group data python scripts/load_public_data.py

# Assemble a weekly MMM outcome dataset through the connector pipeline
uv run --group data python scripts/build_public_mmm_dataset.py
```

> [!TIP]
> Each script writes a provenance-documented summary to `data/public/` (git-ignored) that
> states exactly which fields are real versus imputed. See
> [`docs/phase-41-real-public-data.md`](docs/phase-41-real-public-data.md) and
> [`docs/phase-44-real-connector-mmm.md`](docs/phase-44-real-connector-mmm.md).

## Stakeholder brief and governance demo

```powershell
# One-page business-impact brief (Markdown, plus PDF with the optional brief group)
uv run --group brief python scripts/build_stakeholder_brief.py

# Access-governance walkthrough (RBAC + approval workflow + tamper-evident audit log)
uv run python scripts/governance_demo.py
```

Generated artifacts are written under `.local/` (git-ignored) for local review.

## Project structure

```text
marketing-effectiveness-lab/
├─ app/streamlit_app.py        # Analyst dashboard
├─ streamlit_app.py            # Streamlit Cloud entrypoint
├─ src/marketing_effectiveness_lab/
│  ├─ analytics.py  mmm.py  modeling.py  bayesian.py  uncertainty.py
│  ├─ calibration.py  budget.py  reporting.py  governance.py  artifacts.py
│  ├─ customer.py  access.py
│  └─ data/                    # schema, connectors, assembly, diagnostics, generators,
│                              # online_retail adapter, shared feature definitions
├─ scripts/                    # demo data, real-data, stakeholder brief, governance demo
├─ tests/                      # pytest suite (19 files)
├─ docs/                       # product site (HTML) + phase notes (Markdown)
└─ data/demo/                  # generated demo data (git-ignored)
```

## Documentation

- The **product site** is the entry point: case study, architecture, data contract, and
  product roadmap pages under <https://rosscyking1115.github.io/marketing-effectiveness-lab/>.
- [`docs/data-dictionary.md`](docs/data-dictionary.md) — weekly schema, connector
  templates, and assembly mapping.
- [`docs/production-security-roadmap.md`](docs/production-security-roadmap.md) — security
  and production roadmap, with RBAC/audit marked *demonstrated* and authentication/storage
  *outstanding*.
- `docs/phase-*.md` — chronological design notes for each capability, from baseline
  econometrics through real public data, the stakeholder brief, and access governance.

## Deployment

- **Dashboard** — Streamlit Community Cloud, repository `rosscyking1115/marketing-effectiveness-lab`,
  branch `main`, main file `streamlit_app.py`.
- **Product site** — GitHub Pages serves the `/docs` folder.

---

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution lanes (measurement reliability,
data onboarding, CRM experimentation, production readiness), [`SECURITY.md`](SECURITY.md)
for the public-data policy, and [`LICENSE`](LICENSE) (MIT).
