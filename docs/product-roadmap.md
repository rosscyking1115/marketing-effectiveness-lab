# Product Roadmap

## Mission

Marketing Effectiveness Lab aims to become an open, practical workbench for marketing measurement. The goal is to help teams validate marketing data, estimate channel impact, compare causal evidence, plan budgets, design CRM experiments, and retain reusable learning.

## Current Product State

The current product is a Streamlit prototype backed by a reusable Python package. It supports deterministic demo data, documented CSV contracts, connector validation, MMM-style modelling, experiment calibration, CRM experiment planning, audience exports, calendar planning, readout packaging, a learning library, and a local artifact registry for generated outputs.

It should not yet be used with confidential customer or company data. Production use requires authentication, governed storage, consent controls, audit logs, and deployment hardening.

## Near-Term Product Priorities

1. Governed artifact storage
   - Extend the local artifact registry into durable storage for model runs, uploaded evidence, CRM briefs, audience files, readouts, and learning records.
   - Add authenticated ownership, versioning, approval status, and export history.

2. Safer data onboarding
   - Strengthen connector validation.
   - Add clearer failure messages and remediation guidance.
   - Support warehouse-friendly contracts for aggregated weekly marketing data.

3. Experiment registry
   - Store planned, launched, completed, and archived experiments.
   - Link experiment design, audience assignment, calendar, readout, and learning outcomes.

4. Multi-user governance
   - Separate analyst draft work from approved stakeholder decisions.
   - Add role boundaries, approval states, and audit events.

5. Deployment architecture
   - Move from Streamlit-only prototype toward an API plus production web app.
   - Add database, background jobs, observability, dependency scanning, and secure configuration.

## Contribution Lanes

- Measurement methods: MMM, uncertainty, calibration, diagnostics, causal evidence.
- Data platform: connectors, schemas, storage, data quality, reproducibility.
- CRM experimentation: audience logic, contact policy, readouts, learning library.
- Product engineering: API design, persistence, auth, audit logs, deployment.
- Documentation: examples, product boundaries, governance notes, contribution guides.

## Non-Goals For Now

- Handling raw PII in the public demo.
- Claiming production approval or audit readiness before those controls exist.
- Replacing specialist MMM vendors in high-stakes budget decisions.
- Presenting deterministic demo data as real brand performance.
