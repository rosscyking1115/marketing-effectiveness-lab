# Marketing Effectiveness Lab

An end-to-end marketing effectiveness and MMM project for a UK fashion ecommerce scenario.

The lab is designed as a serious technical portfolio project with a future product path: data foundation, econometrics, marketing mix modeling, causal validation, budget optimization, and executive decision support.

## Live Project

- Portfolio site: <https://rosscyking1115.github.io/marketing-effectiveness-lab/>
- Interactive dashboard: <https://marketing-effectiveness-lab.streamlit.app/>
- GitHub repo: <https://github.com/rosscyking1115/marketing-effectiveness-lab>

## Current Phase

Phase 14: Bayesian MMM foundations.

The project currently includes:

- A documented weekly marketing dataset
- Schema validation
- Analyst dashboarding
- Baseline econometric modeling
- Time-aware holdout diagnostics
- MMM-style adstock and saturation transformations
- Directional contribution and ROI estimates
- Response curves
- Budget scenario planning
- Executive summary generation
- CSV template download and upload validation
- Calibrated MMM adstock/saturation search
- Contribution, ROI, and holdout prediction intervals
- Demo lift-test calibration for contribution, ROI, and uncertainty diagnostics
- Lift-test CSV template and upload validation
- Evidence quality scoring, review flags, and approved-only calibration
- Gross-margin-adjusted profit planning for budget scenarios
- Bayesian posterior contribution, ROI, and holdout prediction intervals
- Experiment-informed media priors from approved lift-test evidence

The next major modeling phase is constrained budget optimization with posterior-aware planning.

## Project Shape

- `docs/` - project briefs, data dictionary, methodology notes
- `src/marketing_effectiveness_lab/` - reusable Python package code
- `scripts/` - runnable project scripts
- `data/demo/` - generated demo data

Useful docs:

- `docs/case-study.md` - business case study
- `docs/architecture.md` - current and future architecture
- `docs/production-security-roadmap.md` - security and production roadmap
- `docs/phase-10-incrementality-calibration.md` - lift-test calibration workflow
- `docs/phase-11-experiment-evidence-upload.md` - real-data-ready experiment evidence upload
- `docs/phase-12-evidence-governance.md` - lift-test quality review and approval filtering
- `docs/phase-13-profit-aware-planning.md` - margin-aware budget scenario planning
- `docs/phase-14-bayesian-mmm-foundations.md` - Bayesian posterior layer and experiment-informed priors

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
