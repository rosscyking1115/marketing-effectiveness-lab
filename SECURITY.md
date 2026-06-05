# Security and Data Handling

Marketing Effectiveness Lab is a public portfolio project and should be treated as a demo analytics application, not a production system.

## Current Data Policy

- The bundled demo dataset is generated from deterministic synthetic code.
- The project does not require API keys, passwords, or third-party service secrets.
- Uploaded CSV files are parsed in memory by the Streamlit app for the active session.
- Do not upload confidential customer, employee, financial, or platform-account data to the public demo app.

## Production Readiness Notes

A production version should add authenticated access, tenant isolation, encrypted object storage, audit logging, secret management, connector OAuth flows, row-level data controls, and formal model approval workflows.

See `docs/production-security-roadmap.md` for the expanded roadmap.

## Reporting Issues

If you find a security issue in this repository, please open a GitHub issue with enough detail to reproduce the problem. Do not include private data, credentials, or confidential exports in the issue.
