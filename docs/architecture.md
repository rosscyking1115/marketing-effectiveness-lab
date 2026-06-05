# Architecture

## Current Architecture

The current project is a local analytics product prototype.

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
    K --> Q["Constrained Budget Optimizer"]
    K --> L["Executive Summary"]
```

## Code Structure

- `src/marketing_effectiveness_lab/data/` handles data generation and schema checks.
- `src/marketing_effectiveness_lab/data/connectors.py` handles connector templates and validation for common marketing exports.
- `src/marketing_effectiveness_lab/data/assembly.py` handles connector-to-weekly assembly for the MMM schema.
- `src/marketing_effectiveness_lab/data/diagnostics.py` handles source coverage and quality checks for assembled connector data.
- `src/marketing_effectiveness_lab/analytics.py` handles dashboard metrics and diagnostics.
- `src/marketing_effectiveness_lab/modeling.py` handles baseline econometrics.
- `src/marketing_effectiveness_lab/mmm.py` handles MMM-style adstock, saturation, contribution, and response curves.
- `src/marketing_effectiveness_lab/uncertainty.py` handles coefficient simulation for contribution and prediction intervals.
- `src/marketing_effectiveness_lab/bayesian.py` handles Bayesian posterior draws, experiment-informed priors, and posterior predictive intervals.
- `src/marketing_effectiveness_lab/calibration.py` handles lift-test templates, upload validation, evidence governance, and experiment calibration.
- `src/marketing_effectiveness_lab/budget.py` handles budget scenario planning, constrained allocation optimization, and profit-aware scenario diagnostics.
- `src/marketing_effectiveness_lab/reporting.py` handles deterministic executive summary generation.
- `app/streamlit_app.py` renders the analyst dashboard.
- `tests/` covers reusable logic.

## Future Product Architecture

The project can evolve into a multi-user internal tool or SaaS product:

```mermaid
flowchart LR
    A["Warehouse or CSV Imports"] --> B["Data Contracts and Validation"]
    B --> C["Feature Pipeline"]
    C --> D["Model Jobs"]
    D --> E["Model Registry"]
    E --> F["API"]
    F --> G["Web App"]
    F --> H["Exports and Reports"]
    I["Auth and RBAC"] --> F
    J["Audit Logs"] --> F
```

Suggested future stack:

- FastAPI for backend APIs
- Postgres for app metadata, users, scenarios, and audit logs
- Dagster for orchestration
- MLflow for model tracking
- dbt for governed marketing marts
- Next.js for a production web app
