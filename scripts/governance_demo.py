"""Demonstrate the access-governance controls end to end.

Simulates a multi-user flow over the RBAC + approval-workflow + audit-log design in
``marketing_effectiveness_lab.access``: a viewer is blocked from running a model, an
analyst runs it and submits a recommendation, separation of duties blocks self-approval,
an approver approves it, exports are permission-gated, and the audit chain is verified
(then deliberately tampered with to show the chain breaks).

Usage:

    uv run python scripts/governance_demo.py

Writes the audit log to ``.local/governance_demo/audit_log.jsonl`` (git-ignored).
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from marketing_effectiveness_lab.access import (
    ApprovalError,
    AuditLog,
    AuthorizationError,
    Permission,
    RecommendationApproval,
    Role,
    authorize,
    role_permission_matrix,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".local" / "governance_demo"


def _attempt(description: str, action) -> None:
    try:
        action()
        print(f"  ALLOWED  {description}")
    except (AuthorizationError, ApprovalError) as exc:
        print(f"  BLOCKED  {description} -> {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the access-governance demonstration.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Role / permission matrix:")
    for row in role_permission_matrix():
        print(f"  {row['role']:<9} {', '.join(row['permissions'])}")
    print()

    audit = AuditLog()
    approval = RecommendationApproval(artifact_id="budget-recommendation-2026-W05")

    print("Governance flow:")
    _attempt(
        "viewer runs the MMM model",
        lambda: authorize(Role.VIEWER, Permission.RUN_MODEL, actor="vic", target="mmm-run", audit=audit),
    )
    _attempt(
        "analyst runs the MMM model",
        lambda: authorize(Role.ANALYST, Permission.RUN_MODEL, actor="ana", target="mmm-run", audit=audit),
    )
    _attempt(
        "analyst submits the recommendation",
        lambda: approval.submit(actor="ana", role=Role.ANALYST, audit=audit),
    )
    _attempt(
        "analyst approves their own recommendation",
        lambda: approval.approve(actor="ana", role=Role.ANALYST, audit=audit),
    )
    _attempt(
        "approver approves the recommendation",
        lambda: approval.approve(actor="boss", role=Role.APPROVER, audit=audit),
    )
    artifact = approval.artifact_id
    _attempt(
        "viewer exports the approved artifact",
        lambda: authorize(Role.VIEWER, Permission.EXPORT_ARTIFACT, actor="vic", target=artifact, audit=audit),
    )
    _attempt(
        "approver exports the approved artifact",
        lambda: authorize(Role.APPROVER, Permission.EXPORT_ARTIFACT, actor="boss", target=artifact, audit=audit),
    )

    print(f"\nFinal approval status: {approval.status.value} (decided by {approval.decided_by}).")
    print(f"Audit events recorded: {len(audit.events())}")
    print(f"Audit chain intact: {audit.verify()}")

    # Show that tampering with a past event is detectable.
    tampered = list(audit.events())
    tampered[1] = dataclasses.replace(tampered[1], outcome="denied")
    print(f"Audit chain intact after tampering with one event: {AuditLog.from_events(tampered).verify()}")

    audit_path = args.output_dir / "audit_log.jsonl"
    audit_path.write_text(audit.to_jsonl() + "\n", encoding="utf-8")
    print(f"\nWrote audit log: {audit_path}")


if __name__ == "__main__":
    main()
