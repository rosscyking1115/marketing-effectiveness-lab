# Security and data handling

Marketing Effectiveness Lab is a public, Apache-2.0 reference implementation. Treat it as a
demo analytics application, not a deployed production system.

## Data policy

- The bundled demo dataset is generated from deterministic synthetic code.
- The project needs no API keys, passwords, or third-party service secrets.
- Uploaded CSV files are parsed in memory by the Streamlit app for the active session only.
  Nothing is persisted.
- Do not upload confidential customer, employee, financial, or platform-account data to the
  public demo app.

## Out of scope

This repository does not implement authenticated access, tenant isolation, encrypted object
storage, audit logging, secret management, connector OAuth flows, row-level data controls, or
model-approval workflows. Anyone adapting the engine for real company data would need to add
those first. [`docs/production-security-roadmap.md`](docs/production-security-roadmap.md) sets
out what that involves.

## Reporting a vulnerability

Email **rosscyking@gmail.com** with enough detail to reproduce the issue. For anything
non-sensitive, a GitHub issue is fine. Either way, please leave out private data, credentials,
and confidential exports.
