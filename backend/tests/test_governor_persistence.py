import pytest

from storage.database import SessionLocal, init_db
from storage.models import Action, AuditEvent

from governor.persistence import (
    persist_action_decision,
)

from governor.schemas import (
    ActionRequest,
    TrustedActionContext,
)


@pytest.fixture(autouse=True)
def clean_persistence_test_data():
    """
    Keep persistence tests isolated.

    These tests use fixed action IDs, so remove any previous
    records with those IDs before and after each test.
    """

    test_action_ids = [
        "test-action-allow-001",
        "test-action-escalate-001",
    ]

    init_db()

    db = SessionLocal()

    try:
        # Remove audit events first because they reference actions.
        db.query(AuditEvent).filter(
            AuditEvent.action_id.in_(test_action_ids)
        ).delete(
            synchronize_session=False
        )

        # Remove the test actions.
        db.query(Action).filter(
            Action.action_id.in_(test_action_ids)
        ).delete(
            synchronize_session=False
        )

        db.commit()

    finally:
        db.close()

    # Run the actual test.
    yield

    # Clean up again after the test.
    db = SessionLocal()

    try:
        db.query(AuditEvent).filter(
            AuditEvent.action_id.in_(test_action_ids)
        ).delete(
            synchronize_session=False
        )

        db.query(Action).filter(
            Action.action_id.in_(test_action_ids)
        ).delete(
            synchronize_session=False
        )

        db.commit()

    finally:
        db.close()


def test_allow_decision_is_persisted():
    init_db()

    db = SessionLocal()

    try:
        request = ActionRequest(
            task_id="sales-report",
            tool="database.read",
            resource="sales_summary",
            arguments={
                "action": "read",
                "columns": [
                    "month",
                    "total_sales",
                ],
            },
        )

        context = TrustedActionContext(
            agent_id="demo-data-analyst",
            role="data_analyst",
            task_scope="sales-report",
            provenance="internal_verified_db",
            environment="local",
        )

        decision = {
            "action_id": "test-action-allow-001",
            "decision": "ALLOW",
            "reason": "Authorized",
            "risk_score": 5,
            "risk_level": "LOW",
            "risk_factors": [],
            "requires_approval": False,
            "latency_ms": 1.2,
        }

        action = persist_action_decision(
            db,
            request,
            context,
            decision,
        )

        assert action.action_id == (
            "test-action-allow-001"
        )

        assert action.decision == "ALLOW"
        assert action.state == "ALLOWED"
        assert action.requires_approval is False

        events = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.action_id
                == action.action_id
            )
            .all()
        )

        assert len(events) == 4

        event_types = [
            event.event_type
            for event in events
        ]

        assert event_types == [
            "ACTION_RECEIVED",
            "AUTHORIZATION_CHECK",
            "RISK_ASSESSMENT",
            "DECISION",
        ]

    finally:
        db.close()


def test_escalated_decision_is_persisted():
    init_db()

    db = SessionLocal()

    try:
        request = ActionRequest(
            task_id="sales-report",
            tool="send.report",
            resource="approved_external_destination",
            arguments={
                "action": "send",
                "destination": "manager@example.com",
            },
        )

        context = TrustedActionContext(
            agent_id="demo-data-analyst",
            role="data_analyst",
            task_scope="sales-report",
            provenance="internal_verified_db",
            environment="local",
        )

        decision = {
            "action_id": "test-action-escalate-001",
            "decision": "ESCALATE",
            "reason": "Human approval required",
            "risk_score": 35,
            "risk_level": "MEDIUM",
            "risk_factors": [
                "external_transfer",
            ],
            "requires_approval": True,
            "latency_ms": 1.5,
        }

        action = persist_action_decision(
            db,
            request,
            context,
            decision,
        )

        assert action.action_id == (
            "test-action-escalate-001"
        )

        assert action.decision == "ESCALATE"

        assert (
            action.state
            == "PENDING_APPROVAL"
        )

        assert (
            action.requires_approval is True
        )

    finally:
        db.close()