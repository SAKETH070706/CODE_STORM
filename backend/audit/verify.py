import json

from audit.integrity import verify_event_hash
from storage.models import AuditEvent


GENESIS_HASH = "GENESIS"


def _event_data(event: AuditEvent) -> dict:
    """
    Reconstruct exactly the same logical event payload
    that record_event() used when creating the hash.
    """

    try:
        details = json.loads(event.details_json)
    except (TypeError, json.JSONDecodeError):
        details = event.details_json

    return {
        "action_id": event.action_id,
        "event_type": event.event_type,
        "details": details,
        "created_at": event.created_at,
    }


def verify_audit_chain(db):
    """
    Verify the complete persisted audit chain.

    Returns:
        (True, "N events verified")
    or
        (False, "reason")
    """

    events = (
        db.query(AuditEvent)
        .order_by(
            AuditEvent.created_at.asc(),
            AuditEvent.id.asc(),
        )
        .all()
    )

    if not events:
        return True, "0 events verified"

    previous_hash = GENESIS_HASH

    for index, event in enumerate(events, start=1):

        event_data = _event_data(event)

        valid = verify_event_hash(
            previous_hash=previous_hash,
            event_data=event_data,
            expected_hash=event.event_hash,
        )

        if not valid:
            return (
                False,
                f"Audit chain verification failed at "
                f"event {index} "
                f"(event_id={event.event_id}).",
            )

        previous_hash = event.event_hash

    return (
        True,
        f"{len(events)} events verified",
    )