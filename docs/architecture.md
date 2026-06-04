# Architecture

## Current Architecture

The current project is a local analytics product prototype.

```mermaid
flowchart LR
    A["Demo or Real Weekly Data"] --> B["Schema Validation"]
    B --> C["Analyst Metrics"]
    C --> D["Streamlit Dashboard"]
    B --> E["Baseline Econometrics"]
    B --> F["MMM Foundations"]
    F --> G["Contribution and ROI"]
    F --> H["Response Curves"]
    H --> I["Budget Scenario Planner"]
    I --> J["Executive Summary"]
```

## Code Structure

- `src/marketing_effectiveness_lab/data/` handles data generation and schema checks.
- `src/marketing_effectiveness_lab/analytics.py` handles dashboard metrics and diagnostics.
- `src/marketing_effectiveness_lab/modeling.py` handles baseline econometrics.
- `src/marketing_effectiveness_lab/mmm.py` handles MMM-style adstock, saturation, contribution, and response curves.
- `src/marketing_effectiveness_lab/budget.py` handles budget scenario planning.
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

