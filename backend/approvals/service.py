import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from governor.schemas import ApprovalState
from approvals.state_machine import transition
from storage.models import Action, Approval


APPROVAL_TTL_SECONDS = 300


# ---------------------------------------------------------
# UTC TIME
# ---------------------------------------------------------

def utc_now() -> datetime:
    """
    Return the current UTC time as a timezone-aware datetime.
    """
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """
    Normalize a datetime to timezone-aware UTC.

    SQLite may return DateTime(timezone=True) values
    as timezone-naive datetimes. This function makes
    them timezone-aware before comparison.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


# ---------------------------------------------------------
# ACTION HASHING
# ---------------------------------------------------------

def canonical_action_data(action: Action) -> dict:
    """
    Build the exact action representation that the approval
    protects.

    The approval is bound to these exact values so that
    changing the action after approval can be detected.
    """

    arguments = json.loads(action.arguments_json or "{}")

    return {
        "action_id": action.action_id,
        "task_id": action.task_id,
        "agent_id": action.agent_id,
        "tool": action.tool,
        "resource": action.resource,
        "arguments": arguments,
        "decision": action.decision,
        "risk_score": action.risk_score,
        "risk_level": action.risk_level,
    }


def calculate_action_hash(action: Action) -> str:
    """
    Generate a deterministic SHA-256 hash for the exact action.
    """

    payload = json.dumps(
        canonical_action_data(action),
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------
# CREATE APPROVAL
# ---------------------------------------------------------

def create_approval(
    db: Session,
    action: Action,
    requested_by: str = "system",
    ttl_seconds: int = APPROVAL_TTL_SECONDS,
) -> Approval:
    """
    Create a human approval request for an ESCALATE action.

    Only ESCALATE actions are eligible for approval.
    """

    if action.decision != "ESCALATE":
        raise ValueError(
            "Only ESCALATE actions can create approvals."
        )

    # Reuse an existing pending approval for the same action.
    existing = (
        db.query(Approval)
        .filter(
            Approval.action_id == action.action_id,
            Approval.state == ApprovalState.PENDING.value,
        )
        .first()
    )

    if existing:
        return existing

    now = utc_now()

    approval = Approval(
        approval_id=str(uuid.uuid4()),
        action_id=action.action_id,
        action_hash=calculate_action_hash(action),
        state=ApprovalState.PENDING.value,
        requested_by=requested_by,
        requested_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )

    # The action is now waiting for human approval.
    action.state = "PENDING_APPROVAL"

    db.add(approval)
    db.commit()
    db.refresh(approval)

    return approval


# ---------------------------------------------------------
# GET APPROVAL
# ---------------------------------------------------------

def get_approval(
    db: Session,
    approval_id: str,
) -> Approval | None:
    """
    Retrieve an approval by its public approval ID.
    """

    return (
        db.query(Approval)
        .filter(Approval.approval_id == approval_id)
        .first()
    )


# ---------------------------------------------------------
# APPROVE
# ---------------------------------------------------------

def approve(
    db: Session,
    approval_id: str,
    decided_by: str,
    reason: str = "Approved by human reviewer",
) -> Approval:
    """
    Approve a pending human approval request.

    PENDING -> APPROVED
    """

    approval = get_approval(db, approval_id)

    if approval is None:
        raise ValueError("Approval not found.")

    current = ApprovalState(approval.state)

    if current != ApprovalState.PENDING:
        raise ValueError(
            f"Approval cannot be approved from state "
            f"{current.value}."
        )

    now = utc_now()

    # Normalize SQLite datetime before comparison.
    expires_at = ensure_utc(approval.expires_at)

    if now >= expires_at:
        approval.state = ApprovalState.EXPIRED.value

        action = (
            db.query(Action)
            .filter(Action.action_id == approval.action_id)
            .first()
        )

        if action:
            action.state = "EXPIRED"

        db.commit()

        raise ValueError("Approval has expired.")

    approval.state = transition(
        current,
        ApprovalState.APPROVED,
    ).value

    approval.decided_by = decided_by
    approval.decision_reason = reason
    approval.decided_at = now

    action = (
        db.query(Action)
        .filter(Action.action_id == approval.action_id)
        .first()
    )

    if action:
        action.state = "APPROVED"

    db.commit()
    db.refresh(approval)

    return approval


# ---------------------------------------------------------
# REJECT
# ---------------------------------------------------------

def reject(
    db: Session,
    approval_id: str,
    decided_by: str,
    reason: str = "Rejected by human reviewer",
) -> Approval:
    """
    Reject a pending human approval request.

    PENDING -> REJECTED
    """

    approval = get_approval(db, approval_id)

    if approval is None:
        raise ValueError("Approval not found.")

    current = ApprovalState(approval.state)

    if current != ApprovalState.PENDING:
        raise ValueError(
            f"Approval cannot be rejected from state "
            f"{current.value}."
        )

    now = utc_now()

    # Normalize SQLite datetime before comparison.
    expires_at = ensure_utc(approval.expires_at)

    if now >= expires_at:
        approval.state = ApprovalState.EXPIRED.value

        action = (
            db.query(Action)
            .filter(Action.action_id == approval.action_id)
            .first()
        )

        if action:
            action.state = "EXPIRED"

        db.commit()

        raise ValueError("Approval has expired.")

    approval.state = transition(
        current,
        ApprovalState.REJECTED,
    ).value

    approval.decided_by = decided_by
    approval.decision_reason = reason
    approval.decided_at = now

    action = (
        db.query(Action)
        .filter(Action.action_id == approval.action_id)
        .first()
    )

    if action:
        action.state = "REJECTED"

    db.commit()
    db.refresh(approval)

    return approval


# ---------------------------------------------------------
# REVALIDATE APPROVAL
# ---------------------------------------------------------

def revalidate_approval(
    db: Session,
    approval_id: str,
) -> Approval:
    """
    Revalidate an approved action before execution.

    This protects against action tampering after approval.

    APPROVED -> REVALIDATED

    If the exact action has changed:
        APPROVED -> REVALIDATION_FAILED
    """

    approval = get_approval(db, approval_id)

    if approval is None:
        raise ValueError("Approval not found.")

    current = ApprovalState(approval.state)

    if current != ApprovalState.APPROVED:
        raise ValueError(
            "Only APPROVED approvals can be revalidated."
        )

    now = utc_now()

    # Normalize SQLite datetime before comparison.
    expires_at = ensure_utc(approval.expires_at)

    if now >= expires_at:
        approval.state = ApprovalState.EXPIRED.value

        action = (
            db.query(Action)
            .filter(Action.action_id == approval.action_id)
            .first()
        )

        if action:
            action.state = "EXPIRED"

        db.commit()

        raise ValueError("Approval has expired.")

    # Retrieve the exact action associated with the approval.
    action = (
        db.query(Action)
        .filter(Action.action_id == approval.action_id)
        .first()
    )

    if action is None:
        raise ValueError("Associated action not found.")

    # Recalculate the action hash.
    current_hash = calculate_action_hash(action)

    # If anything protected by the approval changed,
    # execution must fail closed.
    if current_hash != approval.action_hash:

        approval.state = (
            ApprovalState.REVALIDATION_FAILED.value
        )

        action.state = "REVALIDATION_FAILED"

        db.commit()

        raise ValueError(
            "Revalidation failed: action has changed "
            "since approval."
        )

    # Exact action is still unchanged.
    approval.state = transition(
        current,
        ApprovalState.REVALIDATED,
    ).value

    action.state = "REVALIDATED"

    db.commit()
    db.refresh(approval)

    return approval