# Phase 21: Recommendation Readiness

## Objective

Add explicit review gates before a budget recommendation is treated as ready for stakeholder discussion.

Earlier phases built scenario planning, constrained optimization, and model-run reporting. Phase 21 adds a recommendation-readiness layer so the app can separate a promising scenario from one that needs analyst review or should not advance.

## What Was Added

The reusable package now includes `src/marketing_effectiveness_lab/governance.py`.

It assesses:

- Modeling history length.
- Holdout accuracy.
- Estimated profit impact.
- Size of the proposed spend movement.
- Approved and usable experiment evidence.

The output includes:

- Overall status.
- Readiness score.
- Check-level status table.
- Required actions before approval.

## Dashboard Behavior

The Executive Summary section now shows:

- Review status.
- Readiness score.
- Readiness check table.
- Required actions before approval.

The downloadable model-run report also includes the recommendation-readiness section.

## Status Logic

The current statuses are:

- `Candidate for stakeholder review`: no blocking checks, high readiness score, positive profit impact, and usable approved experiment evidence.
- `Needs analyst review`: no blocking checks, but one or more important review conditions remain.
- `Do not advance`: at least one blocking condition exists.

## Why This Matters

Commercial analytics work should not jump directly from model output to budget approval. A recommendation should be reviewed against model quality, business impact, evidence, and operational risk. This phase makes that judgment explicit while keeping the method transparent.

## Production Boundary

This is a deterministic review aid, not a role-based approval workflow. A production version should persist review decisions, require authenticated approvers, record immutable audit events, and separate analyst recommendations from executive approvals.

## Phase 21 Done Criteria

Phase 21 is complete when:

- Recommendation readiness logic exists in reusable package code.
- Tests cover candidate, review, and block outcomes.
- The dashboard shows status, score, checks, and required actions.
- The model-run report includes recommendation readiness.
- Documentation explains the review gates and production boundary.
