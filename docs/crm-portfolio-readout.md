# Phase 37 - CRM Portfolio Readout Packaging

## Purpose

Phase 37 closes the CRM experimentation loop. The dashboard can now package a scheduled CRM experiment portfolio into a post-launch readout artifact with observed-lift context, incremental profit readout, decision status, recommended next action, and a stakeholder-facing markdown brief.

## What changed

- Added deterministic CRM portfolio readout generation from the launch calendar.
- Joined scheduled experiments back to the ranked CRM experiment comparison table.
- Added CRM benchmark context from existing target-vs-holdout campaign diagnostics.
- Added readout confidence, decision status, recommended next action, and readout notes.
- Added CSV and markdown readout exports.
- Added a Streamlit readout section under the CRM experiment portfolio planner.
- Added tests for deterministic readouts, decision summaries, CSV shape, and markdown brief output.

## Readout logic

The readout package combines:

- Scheduled experiment metadata from the portfolio calendar.
- Planned value and readiness fields from ranked experiment artifacts.
- Existing CRM target-vs-holdout evidence as a benchmark.
- Deterministic decision rules for Scale, Retest, Stop, or Review.

The current implementation is intentionally transparent. It does not pretend that the demo portfolio was truly launched in a CRM platform; instead it shows how a future production system would connect launches, evidence, decisions, and learning records.

## Why this matters

Marketing analytics work is strongest when the loop is complete:

1. Identify a commercial opportunity.
2. Design a test.
3. Assign audiences.
4. Schedule activation.
5. Read out results.
6. Decide whether to scale, retest, stop, or review.

This phase makes the project more credible for commercial data science, CRM analytics, product analytics, and lifecycle marketing roles because it demonstrates the habit of turning analysis into repeatable decision artifacts.

## Production boundary

The readout currently uses deterministic demo logic and benchmark CRM evidence. A production version would need CRM delivery logs, customer-level exposure records, conversion windows, revenue attribution, statistical readout review, experiment registry storage, reviewer identity, approval history, and secure artifact storage.

## Next step

Phase 38 should add an experiment learning library view so CRM readouts can accumulate into reusable evidence by segment, channel, offer, and decision outcome.
