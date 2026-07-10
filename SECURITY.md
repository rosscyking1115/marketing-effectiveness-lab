# Security and Data Handling

Marketing Effectiveness Lab is a public, Apache-2.0 **reference implementation** and should be
treated as a demo analytics application, not a deployed production system.

## Data policy

- The bundled demo dataset is generated from deterministic synthetic code.
- The project does not require API keys, passwords, or third-party service secrets.
- Uploaded CSV files are parsed in memory by the Streamlit app for the active session only; they
  are not persisted.
- Do not upload confidential customer, employee, financial, or platform-account data to the
  public demo app.

## Out of scope for this reference

This repository intentionally does not implement authenticated access, tenant isolation,
encrypted object storage, audit logging, secret management, connector OAuth flows, row-level data
controls, or formal model-approval workflows. Anyone adapting the engine to handle real,
confidential company data would need to add those first — see
[`docs/production-security-roadmap.md`](docs/production-security-roadmap.md) for the considerations.

## Reporting a vulnerability

For a sensitive security issue, please email **rosscyking@gmail.com** with enough detail to
reproduce it. For non-sensitive reports, opening a GitHub issue is fine. Either way, do not
include private data, credentials, or confidential exports.
