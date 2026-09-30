"""Per-organization SHA-256 streams; caller holds the organization row lock."""
import hashlib
import json
from sqlalchemy import select
from core.audit_store import canonical_json
from workspace.models import Organization, AuditEvent, utc


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def append(s, org_id, principal_id, event_type, details):
    org = s.scalar(select(Organization).where(Organization.id == org_id).with_for_update())
    org.audit_sequence += 1
    body = canonical_json({"organization_id": org_id, "sequence": org.audit_sequence, "timestamp": utc(),
                           "principal_id": principal_id, "event_type": event_type, **details})
    hashed = hashlib.sha256((org.audit_head + body).encode()).hexdigest()
    s.add(AuditEvent(organization_id=org_id, sequence=org.audit_sequence, event_json=body,
                     previous_hash=org.audit_head, event_hash=hashed))
    org.audit_head = hashed
    s.flush()


def verify(s, org_id, checkpoint=None):
    previous = "0" * 64
    anchors = {0: previous}
    count = 0
    for event in s.scalars(select(AuditEvent).where(AuditEvent.organization_id == org_id).order_by(AuditEvent.sequence)):
        count += 1
        try:
            parsed = json.loads(event.event_json)
            valid = (event.sequence == count and parsed["sequence"] == count and parsed["organization_id"] == org_id and
                     event.previous_hash == previous and hashlib.sha256((previous + event.event_json).encode()).hexdigest() == event.event_hash)
        except (ValueError, KeyError):
            valid = False
        if not valid:
            return {"valid": False, "broken_at_sequence": event.sequence}
        previous = event.event_hash
        anchors[count] = previous
    org = s.get(Organization, org_id)
    valid = org.audit_sequence == count and org.audit_head == previous
    if checkpoint:
        valid = valid and checkpoint.get("organization_id") == org_id and anchors.get(checkpoint.get("event_count")) == checkpoint.get("head_hash")
    return {"valid": valid, "organization_id": org_id, "event_count": count, "head_hash": previous,
            "protection": "Tamper-evident; retain checkpoints independently. Complete rewrites and unanchored tail deletion are not independently detectable."}
