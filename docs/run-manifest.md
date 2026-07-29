# Phase 22: Model-Run Manifest

## Objective

Add a machine-readable model-run artifact that can support reproducibility, artifact tracking, and future production model-run storage.

Phase 20 created a human-readable markdown report. Phase 21 added recommendation readiness. Phase 22 adds a JSON manifest that captures the same run state in a stable structured format.

## What Was Added

The reusable reporting module now includes:

- `build_model_run_manifest`
- `model_run_manifest_json`

The manifest includes:

- Stable `run_id` derived from the manifest payload.
- Schema version.
- Run context: data source, modeling window, row count, active model, and holdout weeks.
- KPI snapshot.
- Model diagnostics.
- Budget scenario summary.
- Top media contributions.
- Executive summary headline, recommendation, and caveats.
- Recommendation readiness status, score, checks, and required actions.

## Dashboard Behavior

The Executive Summary section now provides two downloads:

- `Download model run report`: human-readable markdown.
- `Download run manifest`: machine-readable JSON.

## Why This Matters

Real analytics systems need more than a dashboard screenshot. They need reproducible artifacts that can be stored, compared, reviewed, and audited. This manifest is a small but practical step toward model-run tracking without adding a database or production storage layer yet.

## Production Boundary

The manifest is downloadable and deterministic, but it is not persisted by the app. A production version should store manifests in governed artifact storage, link them to authenticated users and approvals, and protect them with access controls.

## Phase 22 Done Criteria

Phase 22 is complete when:

- Manifest generation exists in reusable package code.
- The manifest has a stable run id.
- Tests cover manifest structure, deterministic ids, and JSON serialization.
- The Streamlit app exposes a JSON manifest download.
- Documentation explains the reproducibility and production boundary.
