# Phase 43 - Access governance (RBAC, approval workflow, audit log)

The product roadmap names multi-user governance - role boundaries, approval states, and
audit events - as a prerequisite before the tool can handle confidential data. This phase
adds a working **design demonstration** of those controls.

## What it implements

`marketing_effectiveness_lab.access`:

- **Authorization (RBAC).** A fixed, auditable `Role -> Permission` matrix (`viewer`,
  `analyst`, `approver`, `admin`) with `can`, `permissions_for`, and an `authorize`
  helper that records every check to the audit log and raises `AuthorizationError` when a
  role is not permitted.
- **Approval workflow.** `RecommendationApproval` is a `draft -> submitted ->
  approved/rejected` state machine with role gates, valid-transition enforcement, and
  **separation of duties** - the submitter cannot approve or reject their own
  recommendation, even if they hold the approver role.
- **Audit log.** `AuditLog` is append-only and **hash-chained**: every event stores the
  hash of the previous event, so any later edit, deletion, or reordering breaks the chain.
  `verify()` recomputes the chain and returns `False` if it has been tampered with.

## Demonstration

`scripts/governance_demo.py` runs a multi-user flow and prints the result:

```powershell
uv run python scripts/governance_demo.py
```

It shows a viewer blocked from running a model, an analyst running it and submitting a
recommendation, separation of duties blocking self-approval, an approver approving it,
permission-gated exports, a verified audit chain, and the chain breaking once an event is
tampered with. The audit log is written to `.local/governance_demo/` (git-ignored).

## Scope and honesty

This is **authorization and governance**, not **authentication**. The module assumes the
actor's identity has already been established; it does not implement SSO / OIDC / session
management. Wiring real identity in front of it, persisting the audit log to durable
storage, and gating the Streamlit app and artifact registry on these checks remain the
production steps. What is delivered is the testable governance core those steps build on:
the RBAC matrix, the approval state machine with separation of duties, and a
tamper-evident audit trail.
