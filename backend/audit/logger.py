import json
from datetime import datetime, timezone
from uuid import uuid4

from audit.integrity import calculate_event_hash
from storage.models import AuditEvent


GENESIS_HASH = "GENESIS"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_last_event(db):
    return (
        db.query(AuditEvent)
        .order_by(
            AuditEvent.created_at.desc(),
            AuditEvent.id.desc(),
        )
        .first()
    )


def record_event(
    db,
    action_id,
    event_type,
    details,
):
    # ---------------------------------------------------------
    # 1. Find previous event
    # ---------------------------------------------------------
    previous_event = _get_last_event(db)

    previous_hash = (
        previous_event.event_hash
        if previous_event is not None
        else GENESIS_HASH
    )

    # ---------------------------------------------------------
    # 2. Convert details dictionary -> JSON string
    # ---------------------------------------------------------
    details_json = json.dumps(
        details,
        sort_keys=True,
        separators=(",", ":"),
    )

    # ---------------------------------------------------------
    # 3. Generate created_at BEFORE hashing
    # ---------------------------------------------------------
    created_at = utc_now()

    # ---------------------------------------------------------
    # 4. Build logical event data
    # ---------------------------------------------------------
    event_data = {
        "action_id": action_id,
        "event_type": event_type,
        "details": details,
        "created_at": created_at,
    }

    # ---------------------------------------------------------
    # 5. Calculate hash BEFORE inserting into DB
    # ---------------------------------------------------------
    event_hash = calculate_event_hash(
        previous_hash=previous_hash,
        event_data=event_data,
    )

    # ---------------------------------------------------------
    # 6. Create complete AuditEvent
    # ---------------------------------------------------------
    event = AuditEvent(
        event_id=str(uuid4()),
        action_id=action_id,
        event_type=event_type,
        details_json=details_json,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at,
    )

    # ---------------------------------------------------------
    # 7. Persist
    # ---------------------------------------------------------
    db.add(event)
    db.commit()
    db.refresh(event)

    return event