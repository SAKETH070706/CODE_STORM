import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _normalize_datetime(value: Any) -> str:
    """
    Convert datetime values into one canonical UTC ISO-8601 string.

    SQLite may return naive datetimes even when the application originally
    stored timezone-aware UTC datetimes. Canonicalization prevents the hash
    from changing because of that representation difference.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        return value.isoformat()

    return str(value)


def _canonicalize(value: Any) -> Any:
    """
    Recursively convert values into deterministic JSON-compatible data.
    """
    if isinstance(value, datetime):
        return _normalize_datetime(value)

    if isinstance(value, dict):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value.keys(), key=str)
        }

    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]

    return value


def calculate_event_hash(
    previous_hash: str,
    event_data: dict,
) -> str:
    """
    Calculate a deterministic SHA-256 hash for an audit event.

    The previous event hash is included in the calculation, creating a
    tamper-evident hash chain.
    """
    canonical_data = _canonicalize(event_data)

    payload = {
        "previous_hash": previous_hash,
        "event": canonical_data,
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def verify_event_hash(
    previous_hash: str,
    event_data: dict,
    expected_hash: str,
) -> bool:
    """
    Verify one audit event against its stored hash.
    """
    calculated_hash = calculate_event_hash(
        previous_hash,
        event_data,
    )

    return calculated_hash == expected_hash