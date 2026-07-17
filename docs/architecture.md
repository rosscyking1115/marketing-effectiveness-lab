# Architecture

## Current architecture

The project is a reusable Python analytics package with a Streamlit dashboard, run locally on demo
and public data.

```mermaid
flowchart LR
    R["Connector CSV Templates"] --> S["Weekly Assembly Pipeline"]
    S --> T["Source Diagnostics"]
    T --> A["Demo or Real Weekly Data"]
    A --> B["Schema Validation"]
    B --> C["Analyst Metrics"]
    C --> D["Streamlit Dashboard"]
    B --> E["Baseline Econometrics"]
    B --> F["MMM Foundations"]
    F --> G["Contribution and ROI"]
    F --> H["Uncertainty Intervals"]
    M["Lift-Test CSV Upload"] --> N["Evidence Governance"]
    N --> I["Experiment Calibration"]
    N --> O["Bayesian Priors"]
    G --> I
    H --> I
    F --> P["Bayesian Posterior Layer"]
    O --> P
    F --> J["Response Curves"]
    J --> K["Profit-Aware Budget Scenario Planner"]
    K --> Q["Constrained Budget Optimiser"]
    K --> L["Executive Summary"]
```

## Code structure

- `src/marketing_effectiveness_lab/data/` handles data generation and schema checks.
- `data/connectors.py` handles connector templates and validation for commerce, analytics, paid
  media, CRM, affiliate, influencer, display, and external-control exports.
- `data/assembly.py` handles connector-to-weekly assembly for the MMM schema.
- `data/diagnostics.py` handles source coverage and quality checks on assembled connector data.
- `analytics.py` handles dashboard metrics and diagnostics.
- `modeling.py` handles baseline econometrics.
- `mmm.py` handles MMM-style adstock, saturation, contribution, and response curves.
- `uncertainty.py` handles coefficient simulation for contribution and prediction intervals.
- `bayesian.py` handles Bayesian posterior draws, experiment-informed priors, and posterior
  predictive intervals.
- `calibration.py` handles lift-test templates, upload validation, evidence governance, and
  experiment calibration.
- `budget.py` handles budget scenario planning, constrained allocation optimisation, and
  profit-aware scenario diagnostics.
- `governance.py` handles recommendation readiness gates for model fit, profit impact, spend
  movement, history, and evidence.
- `reporting.py` handles deterministic executive summaries, downloadable model-run reports, and
  machine-readable run manifests.
- `app/streamlit_app.py` renders the analyst dashboard.
- `tests/` covers the reusable logic.

## Design notes

The module boundaries are the architecture. Each stage of the measurement workflow (contracts,
assembly, diagnostics, modelling, uncertainty, calibration, budgeting, governance, reporting) is
a separate module with a narrow interface that can be tested on its own. That separation is what
keeps the methodology legible and the engine reusable.

[`methodology.md`](methodology.md) covers the modelling behind `mmm.py`, `uncertainty.py`,
`bayesian.py`, `calibration.py`, and `budget.py`.
