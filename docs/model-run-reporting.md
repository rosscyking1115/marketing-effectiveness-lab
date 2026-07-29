# Phase 20: Model-Run Reporting

## Objective

Add a lightweight review artifact that analysts can download after exploring the dashboard.

The app already generates an executive summary, but real commercial analytics workflows usually need a portable record of the data window, model diagnostics, scenario assumptions, recommendation, and caveats. Phase 20 adds that report export without pretending the prototype has production persistence.

## What Was Added

The reusable reporting module now includes `build_model_run_report`.

The report includes:

- Run context: data source, weekly rows, modeling window, active model, and holdout weeks.
- KPI snapshot: revenue, spend, ROAS, orders, and new customers.
- Model diagnostics: train R-squared, train MAPE, holdout MAPE, and holdout RMSE.
- Top media contribution table.
- Budget scenario summary.
- Recommendation and caveats from the executive summary layer.
- Review notes that clarify the report is not a production approval record.

## Dashboard Behavior

The Executive Summary section now includes a `Download model run report` button.

The downloaded markdown file is generated from the current dashboard state and can be used for:

- Analyst review.
- Stakeholder discussion.
- Portfolio inspection.
- A future model-run tracking workflow.

Phase 22 extends this with a machine-readable JSON manifest for reproducibility and artifact tracking.

## Why This Matters

This moves the project closer to how marketing measurement work is used in practice. The model output is no longer only something viewed in the dashboard; it can be packaged into a reviewable artifact with assumptions and caveats attached.

## Production Boundary

The current report is deterministic and downloadable, but it is not a production audit log. A production version should add authenticated users, persisted model-run records, artifact storage, immutable audit events, approval status, and access controls.

## Phase 20 Done Criteria

Phase 20 is complete when:

- Model-run report generation exists in reusable package code.
- Tests cover the report sections and review notes.
- The Streamlit app exposes a markdown report download.
- Documentation explains the report workflow and production boundary.
