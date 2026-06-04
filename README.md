# Marketing Effectiveness Lab

An end-to-end marketing effectiveness and MMM project for a UK fashion ecommerce scenario.

The lab is designed as a serious technical portfolio project with a future product path: data foundation, econometrics, Bayesian marketing mix modeling, causal validation, and budget optimization.

## Current Phase

Phase 1: Data foundation.

This phase creates a documented weekly marketing dataset that can support:

- Analyst dashboarding
- Baseline econometrics
- Marketing mix modeling
- ROI and contribution analysis
- Budget scenario planning

## Project Shape

- `docs/` - project briefs, data dictionary, methodology notes
- `src/marketing_effectiveness_lab/` - reusable Python package code
- `scripts/` - runnable project scripts
- `data/demo/` - generated demo data

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

Run the test suite:

```powershell
uv run --group dev pytest
```

## Positioning

This project is aimed at the broad commercial data science lane:

- Marketing Data Scientist
- Commercial Data Scientist
- Product/Growth Analyst
- Marketing Analytics Consultant
- Retail/Fashion Data Scientist
