import hashlib
import json
import sqlite3

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent
AUDIT_DB_PATH = BACKEND_DIR / "data" / "governor.db"

GENESIS_HASH = "0" * 64


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def connect_database():
    return sqlite3.connect(
        AUDIT_DB_PATH,
        timeout=5.0,
    )


def initialize_audit_database():
    AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(connect_database()) as connection:
        connection.execute("PRAGMA journal_mode = WAL")

        with connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS actions (
                    request_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    state TEXT NOT NULL,
                    response_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_audit_role
                ON audit_events(role, sequence);
            """)


def action_digest(action) -> str:
    # Bind the event to the exact proposed action.
    # Store its digest rather than arbitrary raw arguments.
    payload = canonical_json(action.model_dump())

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def record_action_event(
    action,
    response: dict,
    phase: str,
):
    event = {
        "request_id": response["request_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "role": response["role"],
        "task_id": action.task_id,
        "tool": action.tool,
        "resource": action.resource,
        "action_digest": action_digest(action),
        "decision": response["decision"],
        "reason_code": response["reason_code"],
        "policy_version": response["policy_version"],
        "state": response["state"],
        "executed": response["executed"],
    }

    with closing(connect_database()) as connection:
        with connection:
            # Serialize writers so simultaneous requests cannot
            # append conflicting audit-chain heads.
            connection.execute("BEGIN IMMEDIATE")

            last_event = connection.execute("""
                SELECT sequence, event_hash
                FROM audit_events
                ORDER BY sequence DESC
                LIMIT 1
            """).fetchone()

            sequence = last_event[0] + 1 if last_event else 1
            previous_hash = (
                last_event[1] if last_event else GENESIS_HASH
            )

            event["sequence"] = sequence
            event_json = canonical_json(event)

            event_hash = hashlib.sha256(
                (previous_hash + event_json).encode("utf-8")
            ).hexdigest()

            connection.execute("""
                INSERT INTO audit_events (
                    sequence,
                    request_id,
                    role,
                    event_json,
                    previous_hash,
                    event_hash
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sequence,
                response["request_id"],
                response["role"],
                event_json,
                previous_hash,
                event_hash,
            ))

            # Action state and its audit event commit together.
            connection.execute("""
                INSERT INTO actions (
                    request_id,
                    role,
                    state,
                    response_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                    state = excluded.state,
                    response_json = excluded.response_json
            """, (
                response["request_id"],
                response["role"],
                response["state"],
                canonical_json(response),
            ))


def get_action(request_id: str, role: str):
    with closing(connect_database()) as connection:
        row = connection.execute("""
            SELECT response_json
            FROM actions
            WHERE request_id = ? AND role = ?
        """, (request_id, role)).fetchone()

    return json.loads(row[0]) if row else None


def get_audit_events(role: str, limit: int = 50):
    with closing(connect_database()) as connection:
        rows = connection.execute("""
            SELECT event_json, previous_hash, event_hash
            FROM audit_events
            WHERE role = ?
            ORDER BY sequence DESC
            LIMIT ?
        """, (role, limit)).fetchall()

    return [
        {
            **json.loads(event_json),
            "previous_hash": previous_hash,
            "event_hash": event_hash,
        }
        for event_json, previous_hash, event_hash in rows
    ]


def verify_audit_chain():
    with closing(connect_database()) as connection:
        rows = connection.execute("""
            SELECT sequence, event_json, previous_hash, event_hash
            FROM audit_events
            ORDER BY sequence
        """).fetchall()

    expected_previous = GENESIS_HASH
    expected_sequence = 1

    for sequence, event_json, previous_hash, event_hash in rows:
        calculated_hash = hashlib.sha256(
            (expected_previous + event_json).encode("utf-8")
        ).hexdigest()

        if (
            sequence != expected_sequence
            or previous_hash != expected_previous
            or event_hash != calculated_hash
        ):
            return {
                "valid": False,
                "broken_at_sequence": sequence,
            }

        expected_previous = event_hash
        expected_sequence += 1

    return {
        "valid": True,
        "event_count": len(rows),
        "head_hash": expected_previous,
        "protection": "Tamper-evident hash chain",
        "limitation": (
            "No external checkpoint yet. A privileged full rewrite "
            "or deletion from the end may evade detection."
        ),
    }