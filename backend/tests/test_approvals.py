import json

import pytest

from approvals.service import (
    calculate_action_hash,
    create_approval,
    approve,
    reject,
    revalidate_approval,
)
from governor.schemas import ApprovalState
from storage.database import SessionLocal, init_db
from storage.models import Action, Approval


# ---------------------------------------------------------
# TEST DATABASE CLEANUP
# ---------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_case5_database():
    """
    Keep Case 5 tests isolated from previous test runs.

    The application uses a persistent SQLite database during
    local development, so pytest must explicitly clean the
    Case 5 records before and after each test.
    """

    init_db()

    db = SessionLocal()

    try:
        # Approval rows reference Action rows, so delete
        # approvals first.
        db.query(Approval).delete(
            synchronize_session=False
        )

        # Remove Case 5 actions from previous runs.
        db.query(Action).filter(
            Action.action_id.like("case5-%")
        ).delete(
            synchronize_session=False
        )

        db.commit()

    finally:
        db.close()

    yield

    # Cleanup after the test as well.
    db = SessionLocal()

    try:
        db.query(Approval).delete(
            synchronize_session=False
        )

        db.query(Action).filter(
            Action.action_id.like("case5-%")
        ).delete(
            synchronize_session=False
        )

        db.commit()

    finally:
        db.close()


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def create_escalated_action(db, action_id):
    """
    Create an ESCALATE action for Case 5 tests.
    """

    action = Action(
        action_id=action_id,
        task_id="sales-report",
        agent_id="demo-data-analyst",
        tool="send.report",
        resource="approved_external_destination",
        arguments_json=json.dumps({
            "action": "send",
            "destination": "manager@example.com",
        }),
        decision="ESCALATE",
        state="PENDING_APPROVAL",
        risk_score=35,
        risk_level="MEDIUM",
        reason="Human approval required",
        requires_approval=True,
    )

    db.add(action)
    db.commit()
    db.refresh(action)

    return action


# ---------------------------------------------------------
# CREATE APPROVAL
# ---------------------------------------------------------

def test_create_approval():
    db = SessionLocal()

    try:
        action = create_escalated_action(
            db,
            "case5-create-001",
        )

        approval = create_approval(
            db,
            action,
            requested_by="demo-agent",
        )

        assert approval.state == "PENDING"
        assert approval.action_id == action.action_id
        assert approval.action_hash
        assert approval.requested_by == "demo-agent"

    finally:
        db.close()


# ---------------------------------------------------------
# ONLY ESCALATE CAN CREATE APPROVAL
# ---------------------------------------------------------

def test_create_approval_only_for_escalate():
    db = SessionLocal()

    try:
        action = Action(
            action_id="case5-allow-001",
            task_id="sales-report",
            agent_id="demo-data-analyst",
            tool="database.read",
            resource="sales_summary",
            arguments_json=json.dumps({
                "action": "read",
                "columns": ["month"],
            }),
            decision="ALLOW",
            state="ALLOWED",
            risk_score=5,
            risk_level="LOW",
            reason="Authorized",
            requires_approval=False,
        )

        db.add(action)
        db.commit()

        with pytest.raises(ValueError):
            create_approval(
                db,
                action,
            )

    finally:
        db.close()


# ---------------------------------------------------------
# APPROVE
# ---------------------------------------------------------

def test_approve_action():
    db = SessionLocal()

    try:
        action = create_escalated_action(
            db,
            "case5-approve-001",
        )

        approval = create_approval(
            db,
            action,
            requested_by="demo-agent",
        )

        approved = approve(
            db,
            approval.approval_id,
            decided_by="admin",
            reason="Approved for demo",
        )

        assert approved.state == "APPROVED"

        db.refresh(action)

        assert action.state == "APPROVED"
        assert approved.decided_by == "admin"

    finally:
        db.close()


# ---------------------------------------------------------
# REJECT
# ---------------------------------------------------------

def test_reject_action():
    db = SessionLocal()

    try:
        action = create_escalated_action(
            db,
            "case5-reject-001",
        )

        approval = create_approval(
            db,
            action,
            requested_by="demo-agent",
        )

        rejected = reject(
            db,
            approval.approval_id,
            decided_by="admin",
            reason="Destination not approved",
        )

        assert rejected.state == "REJECTED"

        db.refresh(action)

        assert action.state == "REJECTED"

    finally:
        db.close()


# ---------------------------------------------------------
# REVALIDATE APPROVED ACTION
# ---------------------------------------------------------

def test_revalidate_approved_action():
    db = SessionLocal()

    try:
        action = create_escalated_action(
            db,
            "case5-revalidate-001",
        )

        approval = create_approval(
            db,
            action,
        )

        approve(
            db,
            approval.approval_id,
            decided_by="admin",
        )

        revalidated = revalidate_approval(
            db,
            approval.approval_id,
        )

        assert revalidated.state == "REVALIDATED"

        db.refresh(action)

        assert action.state == "REVALIDATED"

    finally:
        db.close()


# ---------------------------------------------------------
# TAMPER DETECTION
# ---------------------------------------------------------

def test_revalidation_fails_if_action_changes():
    db = SessionLocal()

    try:
        action = create_escalated_action(
            db,
            "case5-tamper-001",
        )

        approval = create_approval(
            db,
            action,
        )

        approve(
            db,
            approval.approval_id,
            decided_by="admin",
        )

        # Simulate action tampering after approval.
        action.arguments_json = json.dumps({
            "action": "send",
            "destination": "attacker@example.com",
        })

        db.commit()

        with pytest.raises(
            ValueError,
            match="action has changed",
        ):
            revalidate_approval(
                db,
                approval.approval_id,
            )

        db.refresh(approval)
        db.refresh(action)

        assert (
            approval.state
            == "REVALIDATION_FAILED"
        )

        assert (
            action.state
            == "REVALIDATION_FAILED"
        )

    finally:
        db.close()


# ---------------------------------------------------------
# DOUBLE APPROVAL MUST FAIL
# ---------------------------------------------------------

def test_approved_cannot_be_approved_again():
    db = SessionLocal()

    try:
        action = create_escalated_action(
            db,
            "case5-double-approve-001",
        )

        approval = create_approval(
            db,
            action,
        )

        approve(
            db,
            approval.approval_id,
            decided_by="admin",
        )

        with pytest.raises(ValueError):
            approve(
                db,
                approval.approval_id,
                decided_by="admin",
            )

    finally:
        db.close()


# ---------------------------------------------------------
# REJECTED CANNOT BE REVALIDATED
# ---------------------------------------------------------

def test_rejected_action_cannot_be_revalidated():
    db = SessionLocal()

    try:
        action = create_escalated_action(
            db,
            "case5-reject-revalidate-001",
        )

        approval = create_approval(
            db,
            action,
        )

        reject(
            db,
            approval.approval_id,
            decided_by="admin",
        )

        with pytest.raises(ValueError):
            revalidate_approval(
                db,
                approval.approval_id,
            )

    finally:
        db.close()