# Contributing

Marketing Effectiveness Lab is moving from a polished prototype toward a useful open measurement workbench. Contributions should make the tool more reliable, safer to use, easier to extend, or clearer for real marketing analytics workflows.

## Product Principles

- Be honest about what is demo logic and what is production-ready.
- Prefer transparent methods over black-box claims.
- Validate input data before modelling or exporting decisions.
- Keep user-facing workflows explainable to marketing, finance, CRM, and analytics teams.
- Treat security, privacy, consent, and auditability as product requirements, not later polish.

## Good First Contribution Areas

- Add validation checks for uploaded marketing, CRM, or experiment data.
- Improve test coverage around connector diagnostics and CRM experiment workflows.
- Add examples that show how a real aggregated dataset would map into the documented contracts.
- Improve documentation for deployment, security, or model governance.
- Refactor duplicated Streamlit presentation logic into reusable view helpers.

## Production-Grade Contribution Areas

- Persistent artifact storage design for model runs, CRM briefs, audience exports, readouts, and learning records.
- Authentication and role-bound workflow design.
- Audit logs for uploads, model runs, exports, and approval decisions.
- Warehouse or database connector architecture.
- Experiment registry and learning-library persistence.
- API contracts for model runs, calibration evidence, and CRM experiment workflows.

## Local Development

Install dependencies with `uv`, then run:

```powershell
uv run --group dev ruff check .
uv run --group dev pytest
uv run streamlit run app/streamlit_app.py --server.port 8501 --server.headless true
```

## Pull Request Standard

Before opening a PR, include:

- What user problem the change solves.
- Which data contracts or workflows are affected.
- Whether the change is demo-only, production-facing, or production-ready.
- Tests added or updated.
- Any security, privacy, or governance implications.
