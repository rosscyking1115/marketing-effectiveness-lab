# Marketing Effectiveness Lab

An end-to-end marketing effectiveness and MMM project for a UK fashion ecommerce scenario.

The lab is designed as a serious technical portfolio project with a future product path: data foundation, econometrics, Bayesian marketing mix modeling, causal validation, and budget optimization.

## Current Phase

Phase 4: MMM foundations.

The project currently includes:

- A documented weekly marketing dataset
- Schema validation
- Analyst dashboarding
- Baseline econometric modeling
- Time-aware holdout diagnostics
- MMM-style adstock and saturation transformations
- Directional contribution and ROI estimates
- Response curves

The next major modeling phase is calibrated or Bayesian MMM with uncertainty and budget planning.

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
