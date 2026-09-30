from fastapi import APIRouter, HTTPException

from storage.database import (
    SessionLocal,
    init_db,
)

from storage.models import AuditEvent

from audit.verify import (
    verify_audit_chain,
)


router = APIRouter(
    prefix="/api",
    tags=["Audit"],
)


def serialize_event(event):

    return {
        "event_id":
            event.event_id,

        "action_id":
            event.action_id,

        "event_type":
            event.event_type,

        "details":
            event.details_json,

        "previous_hash":
            event.previous_hash,

        "event_hash":
            event.event_hash,

        "created_at":
            event.created_at,
    }


@router.get("/audit")
def get_audit():

    init_db()

    db = SessionLocal()

    try:

        events = (
            db.query(AuditEvent)
            .order_by(
                AuditEvent.created_at.asc()
            )
            .limit(500)
            .all()
        )

        valid, message = (
            verify_audit_chain(db)
        )

        return {
            "valid": valid,
            "message": message,
            "count": len(events),
            "events": [
                serialize_event(event)
                for event in events
            ],
        }

    finally:

        db.close()