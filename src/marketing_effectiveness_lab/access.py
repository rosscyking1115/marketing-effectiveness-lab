"""Access governance: role-based permissions, an approval workflow, and an audit log.

This module is a **design demonstration** of the governance controls a production
deployment needs before it can handle confidential data. It implements:

- **Authorization (RBAC):** a fixed role -> permission matrix and helpers to check it.
- **Approval workflow:** a draft -> submitted -> approved/rejected state machine with
  role gates and separation of duties (an approver cannot approve their own submission).
- **Audit log:** an append-only, hash-chained event log that can detect tampering.

It deliberately does **not** implement *authentication* (verifying identity via SSO /
OIDC / sessions). The caller is assumed to have already authenticated the actor; this
module governs what an authenticated role may do and records what happened. Wiring real
identity in front of it remains a production dependency (see the security roadmap).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

GENESIS_HASH = "0" * 64


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    APPROVER = "approver"
    ADMIN = "admin"


class Permission(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"
    RUN_MODEL = "run_model"
    UPLOAD_EVIDENCE = "upload_evidence"
    SUBMIT_RECOMMENDATION = "submit_recommendation"
    APPROVE_RECOMMENDATION = "approve_recommendation"
    EXPORT_ARTIFACT = "export_artifact"
    MANAGE_USERS = "manage_users"


# Role -> permissions. Roles are cumulative in practice but defined explicitly so the
# matrix is auditable rather than implied by inheritance.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.VIEW_DASHBOARD}),
    Role.ANALYST: frozenset(
        {
            Permission.VIEW_DASHBOARD,
            Permission.RUN_MODEL,
            Permission.UPLOAD_EVIDENCE,
            Permission.SUBMIT_RECOMMENDATION,
            Permission.EXPORT_ARTIFACT,
        }
    ),
    Role.APPROVER: frozenset(
        {
            Permission.VIEW_DASHBOARD,
            Permission.RUN_MODEL,
            Permission.UPLOAD_EVIDENCE,
            Permission.SUBMIT_RECOMMENDATION,
            Permission.APPROVE_RECOMMENDATION,
            Permission.EXPORT_ARTIFACT,
        }
    ),
    Role.ADMIN: frozenset(Permission),
}


class AuthorizationError(PermissionError):
    """Raised when a role attempts an action it is not permitted to perform."""


class ApprovalError(RuntimeError):
    """Raised on an invalid approval-workflow transition or separation-of-duties breach."""


def permissions_for(role: Role) -> frozenset[Permission]:
    """Return the permission set granted to a role."""

    return ROLE_PERMISSIONS.get(role, frozenset())


def can(role: Role, permission: Permission) -> bool:
    """Return whether a role holds a permission."""

    return permission in permissions_for(role)


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    timestamp: str
    actor: str
    role: str
    action: str
    target: str
    outcome: str
    details: dict[str, object]
    previous_hash: str
    entry_hash: str

    def payload(self) -> dict[str, object]:
        """The hashed content of the event (everything except its own hash)."""

        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "role": self.role,
            "action": self.action,
            "target": self.target,
            "outcome": self.outcome,
            "details": self.details,
            "previous_hash": self.previous_hash,
        }


def _hash_payload(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditLog:
    """An append-only, hash-chained audit log.

    Each event stores the hash of the previous event, so any later edit or deletion
    breaks the chain and is detectable via :meth:`verify`.
    """

    def __init__(self, *, now: Callable[[], datetime] | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._now = now or (lambda: datetime.now(UTC))

    def record(
        self,
        *,
        actor: str,
        role: Role | str,
        action: str,
        target: str,
        outcome: str = "ok",
        details: Mapping[str, object] | None = None,
        timestamp: str | None = None,
    ) -> AuditEvent:
        sequence = len(self._events)
        previous_hash = self._events[-1].entry_hash if self._events else GENESIS_HASH
        payload = {
            "sequence": sequence,
            "timestamp": timestamp or self._now().isoformat(),
            "actor": actor,
            "role": str(getattr(role, "value", role)),
            "action": action,
            "target": target,
            "outcome": outcome,
            "details": dict(details or {}),
            "previous_hash": previous_hash,
        }
        event = AuditEvent(**payload, entry_hash=_hash_payload(payload))
        self._events.append(event)
        return event

    def events(self) -> list[AuditEvent]:
        return list(self._events)

    def verify(self) -> bool:
        """Return True if the hash chain is intact (no tampering or reordering)."""

        previous_hash = GENESIS_HASH
        for index, event in enumerate(self._events):
            if event.sequence != index or event.previous_hash != previous_hash:
                return False
            if _hash_payload(event.payload()) != event.entry_hash:
                return False
            previous_hash = event.entry_hash
        return True

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(event.payload() | {"entry_hash": event.entry_hash}) for event in self._events)

    @classmethod
    def from_events(cls, events: Sequence[AuditEvent]) -> AuditLog:
        log = cls()
        log._events = list(events)
        return log


def authorize(
    role: Role,
    permission: Permission,
    *,
    actor: str,
    target: str,
    audit: AuditLog | None = None,
    details: Mapping[str, object] | None = None,
) -> None:
    """Check a permission, record the attempt to the audit log, and raise if denied."""

    allowed = can(role, permission)
    if audit is not None:
        audit.record(
            actor=actor,
            role=role,
            action=permission.value,
            target=target,
            outcome="allowed" if allowed else "denied",
            details=details,
        )
    if not allowed:
        raise AuthorizationError(f"Role '{role.value}' lacks permission '{permission.value}'.")


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class RecommendationApproval:
    """A reviewable recommendation moving through the approval workflow.

    Enforces role gates, valid transitions, and separation of duties, recording every
    transition to the supplied audit log.
    """

    artifact_id: str
    status: ApprovalStatus = ApprovalStatus.DRAFT
    submitted_by: str | None = None
    decided_by: str | None = None
    history: list[dict[str, object]] = field(default_factory=list)

    def submit(self, *, actor: str, role: Role, audit: AuditLog) -> None:
        if self.status != ApprovalStatus.DRAFT:
            raise ApprovalError(f"Can only submit a draft; current status is '{self.status.value}'.")
        authorize(
            role,
            Permission.SUBMIT_RECOMMENDATION,
            actor=actor,
            target=self.artifact_id,
            audit=audit,
        )
        self.status = ApprovalStatus.SUBMITTED
        self.submitted_by = actor
        self._log(audit, actor, role, "submit")

    def approve(self, *, actor: str, role: Role, audit: AuditLog) -> None:
        self._decide(actor=actor, role=role, audit=audit, approve=True)

    def reject(self, *, actor: str, role: Role, audit: AuditLog, reason: str = "") -> None:
        self._decide(actor=actor, role=role, audit=audit, approve=False, reason=reason)

    def _decide(self, *, actor: str, role: Role, audit: AuditLog, approve: bool, reason: str = "") -> None:
        if self.status != ApprovalStatus.SUBMITTED:
            raise ApprovalError(
                f"Can only decide a submitted recommendation; current status is '{self.status.value}'."
            )
        # Separation of duties: the submitter may not approve or reject their own work.
        if actor == self.submitted_by:
            audit.record(
                actor=actor,
                role=role,
                action=Permission.APPROVE_RECOMMENDATION.value,
                target=self.artifact_id,
                outcome="denied",
                details={"reason": "separation_of_duties"},
            )
            raise ApprovalError("Separation of duties: the submitter cannot decide their own recommendation.")
        authorize(
            role,
            Permission.APPROVE_RECOMMENDATION,
            actor=actor,
            target=self.artifact_id,
            audit=audit,
        )
        self.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        self.decided_by = actor
        self._log(audit, actor, role, "approve" if approve else "reject", reason=reason)

    def _log(self, audit: AuditLog, actor: str, role: Role, transition: str, reason: str = "") -> None:
        entry = {
            "transition": transition,
            "status": self.status.value,
            "actor": actor,
            "role": role.value,
        }
        if reason:
            entry["reason"] = reason
        self.history.append(entry)


def role_permission_matrix() -> list[dict[str, object]]:
    """Return the RBAC matrix as serializable records for display or export."""

    return [
        {
            "role": role.value,
            "permissions": sorted(permission.value for permission in permissions_for(role)),
        }
        for role in Role
    ]
