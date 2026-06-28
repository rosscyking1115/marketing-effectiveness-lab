# Phase 40 - Local Artifact Registry

## Purpose

Phase 40 adds the first persistence foundation. The app can now write generated model and CRM artifacts into a local registry with stable IDs, content hashes, metadata, and an index.

This is not full production storage. It is a concrete local contract that future database, object-storage, authentication, and audit-log work can replace behind a similar artifact interface.

## What Changed

- Added `src/marketing_effectiveness_lab/artifacts.py` with filesystem-backed artifact persistence.
- Added registry metadata records with artifact type, artifact ID, content path, MIME type, SHA-256 hash, byte size, timestamp, and metadata.
- Added deterministic JSON persistence for model-run manifests.
- Added index loading, tabular display, text/byte reading, and content-hash verification helpers.
- Added Streamlit actions to persist the current model-run report and manifest.
- Added Streamlit actions to persist CRM portfolio plan, launch calendar, readout CSV, readout brief, and learning library.
- Added `.local/` to `.gitignore` so local artifact payloads are not committed.
- Added tests for persistence, JSON serialization, index filtering, upsert behavior, and unsafe identifier rejection.

## Registry Shape

The local registry writes files under:

```text
.local/artifact_registry/
```

Example artifact families:

- `model_run_manifest`
- `model_run_report`
- `crm_portfolio_plan`
- `crm_portfolio_calendar`
- `crm_portfolio_readout`
- `crm_portfolio_readout_brief`
- `crm_learning_library`

The registry index is:

```text
.local/artifact_registry/artifact_index.json
```

## Product Boundary

The registry is useful for local review, reproducibility, and product workflow testing. On Streamlit Cloud, filesystem persistence is ephemeral. For confidential company data or multi-user use, the product still needs:

- Authentication and user ownership.
- Durable object storage or database-backed artifact records.
- Approval states and immutable audit events.
- Access control by team, market, brand, and artifact type.
- Retention policy and deletion workflows.

## Why This Matters

The project has moved beyond downloadable files only. A user can now save generated evidence into a local indexed store, inspect what exists, and verify that files still match their recorded hashes.

That is the first small production-grade step toward model-run tracking, CRM experiment registries, and reusable learning records.

## Next Step

Phase 41 should turn the registry into a first-class artifact review workflow, such as loading registered artifacts back into the dashboard for comparison without manual upload.
