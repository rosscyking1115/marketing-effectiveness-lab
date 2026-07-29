# Phase 36 - CRM Portfolio Launch Calendar

## Purpose

Phase 36 turns the mutually exclusive CRM portfolio audience export into a lightweight launch calendar. The dashboard can now stage ranked experiments across launch windows, check spacing against a contact-policy cooldown, and flag weekly contact-load pressure before an analyst downloads activation files.

## What changed

- Added deterministic CRM experiment portfolio calendar generation.
- Added launch dates, launch-week grouping, cooldown end dates, and measurement end dates.
- Added weekly contact-load checks against a configurable contact cap.
- Added launch-spacing checks against a configurable cooldown window.
- Added calendar summary metrics and a CSV export.
- Added Streamlit controls for first launch date, launch spacing, weekly cap, and cooldown days.
- Added tests for deterministic calendar generation, spacing guardrails, summary metrics, and CSV shape.

## Planning logic

The calendar is built from the portfolio audience export:

- One row is created per selected experiment.
- Launch order follows the portfolio priority rank.
- Launch dates are spaced from the selected first launch date.
- Weekly load is calculated from assigned customers scheduled in the same launch week.
- Experiments are flagged for review when launches fall inside the cooldown window.
- Experiments are also flagged when the scheduled weekly contact load exceeds the selected cap.

## Why this matters

CRM testing is not only a modelling problem. A strong commercial data scientist needs to show that recommendations can survive operational constraints: campaign capacity, customer contact policy, measurement windows, and stakeholder launch planning.

This phase makes the project stronger for marketing analytics, CRM, product analytics, and commercial data science roles because it connects modelling outputs to a realistic activation workflow.

## Production boundary

The current calendar uses deterministic demo audiences and local planning rules. A production version would need live campaign calendars, customer-level contact history, suppression lists, consent refreshes, CRM platform delivery logs, approval workflows, and role-based governance before activation.

## Next step

Phase 37 should add post-launch readout packaging for CRM experiments, so scheduled launches can be connected back to measured uplift, decision status, and future portfolio learning.
