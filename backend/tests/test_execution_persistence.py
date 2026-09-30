import json

from storage.database import SessionLocal, init_db
from storage.models import Action

from execution.persistence import (
    create_execution,
    complete_execution,
    fail_execution,
)


def create_test_action(db):
    action = Action(
        task_id="sales-report",
        agent_id="demo-data-analyst",
        tool="database.read",
        resource="sales_summary",
        arguments_json=json.dumps(
            {
                "columns": ["month"],
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

    return action


def test_execution_completed():
    init_db()

    db = SessionLocal()

    try:
        action = create_test_action(db)

        execution = create_execution(
            db,
            action.action_id,
        )

        assert execution.status == "STARTED"

        complete_execution(
            db,
            execution,
            {
                "rows": 6,
            },
        )

        assert execution.status == "COMPLETED"
        assert execution.completed_at is not None
        assert execution.result_json is not None

    finally:
        db.close()


def test_execution_failed():
    init_db()

    db = SessionLocal()

    try:
        action = create_test_action(db)

        execution = create_execution(
            db,
            action.action_id,
        )

        error = RuntimeError(
            "Simulated execution failure"
        )

        fail_execution(
            db,
            execution,
            error,
        )

        assert execution.status == "FAILED"
        assert execution.error == str(error)
        assert execution.completed_at is not None

    finally:
        db.close()