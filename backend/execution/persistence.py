import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from storage.models import Execution

from audit.logger import record_event


def utc_now():
    return datetime.now(timezone.utc)


def create_execution(
    db: Session,
    action_id: str,
) -> Execution:
    """
    Create an execution record.
    """

    execution = Execution(
        action_id=action_id,
        status="STARTED",
        started_at=utc_now(),
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    record_event(
        db=db,
        action_id=action_id,
        event_type="EXECUTION_STARTED",
        details={
            "execution_id": execution.execution_id,
        },
    )

    return execution


def complete_execution(
    db: Session,
    execution: Execution,
    result,
) -> Execution:
    """
    Mark execution as successfully completed.
    """

    execution.status = "COMPLETED"

    execution.result_json = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    execution.completed_at = utc_now()

    db.commit()
    db.refresh(execution)

    record_event(
        db=db,
        action_id=execution.action_id,
        event_type="EXECUTION_COMPLETED",
        details={
            "execution_id": execution.execution_id,
        },
    )

    return execution


def fail_execution(
    db: Session,
    execution: Execution,
    error: Exception,
) -> Execution:
    """
    Mark execution as failed.
    """

    execution.status = "FAILED"

    execution.error = str(error)

    execution.completed_at = utc_now()

    db.commit()
    db.refresh(execution)

    record_event(
        db=db,
        action_id=execution.action_id,
        event_type="EXECUTION_FAILED",
        details={
            "execution_id": execution.execution_id,
            "error": str(error),
        },
    )

    return execution