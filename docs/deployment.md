# Deployment Guide

## Streamlit Community Cloud

Use these settings in the deploy form:

- Repository: `rosscyking1115/marketing-effectiveness-lab`
- Branch: `main`
- Main file path: `streamlit_app.py`
- App URL suggestion: `marketing-effectiveness-lab`
- Python version: `3.12`

The root `streamlit_app.py` file launches the dashboard in `app/streamlit_app.py` and adds `src/` to the Python path for deployment reliability.

## Dependency Handling

The repository includes `uv.lock` and `pyproject.toml`.

Streamlit Community Cloud recognizes `uv.lock` as a dependency file and searches the app directory before the repository root. The lock file is at the repository root, so it is available for the root Streamlit entrypoint.

## Data Handling

The demo CSV files are not committed. On first run, the app generates the demo dataset from deterministic package code and writes it to `data/demo/`.

No secrets are required for the current version.

## GitHub Pages Portfolio Site

Use GitHub Pages for the static case-study presentation and Streamlit for the interactive dashboard.

Recommended GitHub Pages settings:

- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/docs`

The static site entrypoint is `docs/index.html`.
