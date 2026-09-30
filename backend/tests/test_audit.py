import json

from storage.database import SessionLocal, init_db
from storage.models import Action, AuditEvent

from audit.logger import record_event
from audit.verify import verify_audit_chain


def test_audit_event_is_persisted():
    init_db()

    db = SessionLocal()

    try:
        action = Action(
            task_id="sales-report",
            agent_id="demo-data-analyst",
            tool="database.read",
            resource="sales_summary",
            arguments_json=json.dumps(
                {
                    "columns": [
                        "month",
                        "total_sales",
                    ]
                }
            ),
            decision="ALLOW",
            state="ALLOWED",
            risk_score=5,
            risk_level="LOW",
            reason="Authorized",
            requires_approval=False,
        )

        db.add(action)
        db.commit()
        db.refresh(action)

        event = record_event(
            db=db,
            action_id=action.action_id,
            event_type="ACTION_RECEIVED",
            details={
                "tool": "database.read",
            },
        )

        assert event.event_id is not None
        assert event.action_id == action.action_id
        assert event.event_type == "ACTION_RECEIVED"
        assert event.event_hash is not None

    finally:
        db.close()


def test_audit_chain_links_events():
    init_db()

    db = SessionLocal()

    try:
        action = Action(
            task_id="sales-report",
            agent_id="demo-data-analyst",
            tool="database.read",
            resource="sales_summary",
            arguments_json="{}",
            decision="ALLOW",
            state="ALLOWED",
            risk_score=5,
            risk_level="LOW",
            reason="Authorized",
            requires_approval=False,
        )

        db.add(action)
        db.commit()
        db.refresh(action)

        first = record_event(
            db=db,
            action_id=action.action_id,
            event_type="ACTION_RECEIVED",
            details={"step": 1},
        )

        second = record_event(
            db=db,
            action_id=action.action_id,
            event_type="DECISION",
            details={"decision": "ALLOW"},
        )

        assert (
            second.previous_hash
            == first.event_hash
        )

    finally:
        db.close()


def test_audit_chain_is_valid():
    init_db()

    db = SessionLocal()

    try:
        action = Action(
            task_id="audit-test",
            agent_id="demo-data-analyst",
            tool="database.read",
            resource="sales_summary",
            arguments_json="{}",
            decision="ALLOW",
            state="ALLOWED",
            risk_score=5,
            risk_level="LOW",
            reason="Authorized",
            requires_approval=False,
        )

        db.add(action)
        db.commit()
        db.refresh(action)

        record_event(
            db,
            action.action_id,
            "ACTION_RECEIVED",
            {"test": True},
        )

        record_event(
            db,
            action.action_id,
            "DECISION",
            {"decision": "ALLOW"},
        )

        valid, message = verify_audit_chain(db)

        assert valid is True
        assert "events verified" in message

    finally:
        db.close()