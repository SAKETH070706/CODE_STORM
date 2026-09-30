from audit.integrity import (
    calculate_event_hash,
    verify_event_hash,
)


def test_hash_is_deterministic():
    event_data = {
        "action_id": "action-1",
        "event_type": "DECISION",
        "details": {
            "decision": "ALLOW",
        },
        "created_at": (
            "2026-09-30T10:00:00+00:00"
        ),
    }

    first = calculate_event_hash(
        "previous",
        event_data,
    )

    second = calculate_event_hash(
        "previous",
        event_data,
    )

    assert first == second


def test_hash_changes_when_data_changes():
    event_data = {
        "action_id": "action-1",
        "event_type": "DECISION",
        "details": {
            "decision": "ALLOW",
        },
        "created_at": (
            "2026-09-30T10:00:00+00:00"
        ),
    }

    original_hash = calculate_event_hash(
        "previous",
        event_data,
    )

    modified_data = {
        **event_data,
        "details": {
            "decision": "BLOCK",
        },
    }

    modified_hash = calculate_event_hash(
        "previous",
        modified_data,
    )

    assert original_hash != modified_hash


def test_modified_event_fails_verification():
    event_data = {
        "action_id": "action-1",
        "event_type": "DECISION",
        "details": {
            "decision": "ALLOW",
        },
        "created_at": (
            "2026-09-30T10:00:00+00:00"
        ),
    }

    event_hash = calculate_event_hash(
        "previous",
        event_data,
    )

    assert verify_event_hash(
        "previous",
        event_data,
        event_hash,
    )

    modified_data = {
        **event_data,
        "details": {
            "decision": "BLOCK",
        },
    }

    assert not verify_event_hash(
        "previous",
        modified_data,
        event_hash,
    )