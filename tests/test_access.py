from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from marketing_effectiveness_lab.access import (
    ApprovalError,
    ApprovalStatus,
    AuditLog,
    AuthorizationError,
    Permission,
    RecommendationApproval,
    Role,
    authorize,
    can,
    permissions_for,
    role_permission_matrix,
)


def _fixed_clock():
    return AuditLog(now=lambda: datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC))


def test_role_permission_matrix_is_least_privilege() -> None:
    assert permissions_for(Role.VIEWER) == frozenset({Permission.VIEW_DASHBOARD})
    assert can(Role.ANALYST, Permission.SUBMIT_RECOMMENDATION)
    assert not can(Role.ANALYST, Permission.APPROVE_RECOMMENDATION)
    assert can(Role.APPROVER, Permission.APPROVE_RECOMMENDATION)
    assert not can(Role.VIEWER, Permission.RUN_MODEL)
    # Only admin manages users.
    assert can(Role.ADMIN, Permission.MANAGE_USERS)
    assert not can(Role.APPROVER, Permission.MANAGE_USERS)
    assert {row["role"] for row in role_permission_matrix()} == {r.value for r in Role}


def test_authorize_allows_and_audits() -> None:
    audit = _fixed_clock()
    authorize(Role.ANALYST, Permission.RUN_MODEL, actor="ana", target="run-1", audit=audit)

    events = audit.events()
    assert len(events) == 1
    assert events[0].outcome == "allowed"
    assert events[0].action == "run_model"


def test_authorize_denies_records_and_raises() -> None:
    audit = _fixed_clock()
    with pytest.raises(AuthorizationError):
        authorize(Role.VIEWER, Permission.RUN_MODEL, actor="vic", target="run-1", audit=audit)

    assert audit.events()[-1].outcome == "denied"


def test_approval_workflow_happy_path() -> None:
    audit = _fixed_clock()
    approval = RecommendationApproval(artifact_id="rec-1")

    approval.submit(actor="ana", role=Role.ANALYST, audit=audit)
    assert approval.status == ApprovalStatus.SUBMITTED
    approval.approve(actor="boss", role=Role.APPROVER, audit=audit)

    assert approval.status == ApprovalStatus.APPROVED
    assert approval.submitted_by == "ana"
    assert approval.decided_by == "boss"
    assert [entry["transition"] for entry in approval.history] == ["submit", "approve"]


def test_approval_enforces_separation_of_duties() -> None:
    audit = _fixed_clock()
    approval = RecommendationApproval(artifact_id="rec-1")
    # The submitter happens to also hold the approver role, but still may not self-approve.
    approval.submit(actor="dual", role=Role.APPROVER, audit=audit)

    with pytest.raises(ApprovalError, match="Separation of duties"):
        approval.approve(actor="dual", role=Role.APPROVER, audit=audit)

    assert approval.status == ApprovalStatus.SUBMITTED
    assert audit.events()[-1].outcome == "denied"


def test_approval_requires_permission_and_valid_transition() -> None:
    audit = _fixed_clock()
    approval = RecommendationApproval(artifact_id="rec-1")

    # Cannot approve before submission.
    with pytest.raises(ApprovalError):
        approval.approve(actor="boss", role=Role.APPROVER, audit=audit)

    # A viewer cannot submit.
    with pytest.raises(AuthorizationError):
        approval.submit(actor="vic", role=Role.VIEWER, audit=audit)

    # A non-submitter analyst lacks approve permission (passes separation of duties).
    approval.submit(actor="ana", role=Role.ANALYST, audit=audit)
    with pytest.raises(AuthorizationError):
        approval.approve(actor="ana2", role=Role.ANALYST, audit=audit)


def test_audit_log_is_hash_chained_and_tamper_evident() -> None:
    audit = _fixed_clock()
    audit.record(actor="ana", role=Role.ANALYST, action="run_model", target="run-1")
    audit.record(actor="boss", role=Role.APPROVER, action="approve_recommendation", target="rec-1")

    events = audit.events()
    assert [event.sequence for event in events] == [0, 1]
    assert events[1].previous_hash == events[0].entry_hash
    assert audit.verify()
    assert audit.to_jsonl().count("\n") == 1  # two lines, one separator

    # Tampering with a recorded field breaks the chain.
    tampered = list(events)
    tampered[0] = dataclasses.replace(tampered[0], actor="attacker")
    assert AuditLog.from_events(tampered).verify() is False

    # Reordering also breaks it.
    assert AuditLog.from_events(list(reversed(events))).verify() is False
