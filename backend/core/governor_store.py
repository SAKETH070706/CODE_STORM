"""SQLite persistence boundary; migrations never rewrite the legacy audit chain."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from core.audit_store import canonical_json, GENESIS_HASH


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class Store:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self, write=False):
        c = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA busy_timeout=10000")
            c.execute("PRAGMA synchronous=FULL")
            c.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield c
            c.commit()
        except BaseException:
            try:
                c.rollback()
            except Exception:
                pass
            raise
        finally:
            c.close()

    def migrate(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(self.path, timeout=10.0)
        try:
            c.execute("PRAGMA journal_mode=WAL")
        finally:
            c.close()
        with self.connection(True) as c:
            c.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            versions = [r[0] for r in c.execute("SELECT version FROM schema_migrations")]
            if any(v > 1 for v in versions):
                raise RuntimeError("Database schema is newer than this application")
            if 1 in versions:
                return
            statements = [
                "CREATE TABLE IF NOT EXISTS actions(request_id TEXT PRIMARY KEY, role TEXT NOT NULL, state TEXT NOT NULL, response_json TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS audit_events(sequence INTEGER PRIMARY KEY, request_id TEXT NOT NULL, role TEXT NOT NULL, event_json TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)",
                "CREATE TABLE governed_actions(request_id TEXT PRIMARY KEY REFERENCES actions(request_id), principal_id TEXT NOT NULL, action_json TEXT NOT NULL, action_digest TEXT NOT NULL, policy_version TEXT NOT NULL, context_digest TEXT NOT NULL, created_at TEXT NOT NULL, expires_at REAL NOT NULL, evaluation_only INTEGER NOT NULL)",
                "CREATE TABLE task_assignments(principal_id TEXT NOT NULL, role TEXT NOT NULL, task_id TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(principal_id, task_id))",
                "CREATE TABLE idempotency(principal_id TEXT NOT NULL, key TEXT NOT NULL, payload_digest TEXT NOT NULL, request_id TEXT NOT NULL REFERENCES actions(request_id), PRIMARY KEY(principal_id,key))",
                "CREATE TABLE approvals(request_id TEXT PRIMARY KEY REFERENCES actions(request_id), reviewer_id TEXT NOT NULL, decision TEXT NOT NULL, comment TEXT NOT NULL, decided_at TEXT NOT NULL, action_digest TEXT NOT NULL)",
                "CREATE TABLE artifacts(artifact_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, task_id TEXT NOT NULL, resource TEXT NOT NULL, kind TEXT NOT NULL, sensitivity TEXT NOT NULL, content_digest TEXT NOT NULL, data_json TEXT NOT NULL, source_id TEXT, created_at TEXT NOT NULL)",
                "CREATE TABLE outbox(request_id TEXT PRIMARY KEY REFERENCES actions(request_id), artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id), destination TEXT NOT NULL, delivery_mode TEXT NOT NULL CHECK(delivery_mode='simulated'), created_at TEXT NOT NULL)",
                "CREATE INDEX governed_owner ON governed_actions(principal_id)",
            ]
            for statement in statements:
                c.execute(statement)
            c.executemany("INSERT INTO task_assignments(principal_id,role,task_id) VALUES(?,?,?)", [
                ("analyst-1", "data_analyst", "sales-report"),
                ("support-1", "customer_support", "support-review"),
            ])
            c.execute("INSERT INTO schema_migrations VALUES(1,?)", (now(),))

    def append(self, c, event):
        head = c.execute("SELECT sequence,event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
        sequence, previous = (head[0] + 1, head[1]) if head else (1, GENESIS_HASH)
        event = {**event, "timestamp": now(), "sequence": sequence}
        encoded = canonical_json(event)
        h = hashlib.sha256((previous + encoded).encode()).hexdigest()
        c.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?)", (sequence, event["request_id"], event["role"], encoded, previous, h))

    def save(self, c, response, metadata, previous=None, reviewer=None):
        c.execute("INSERT INTO actions VALUES(?,?,?,?) ON CONFLICT(request_id) DO UPDATE SET state=excluded.state,response_json=excluded.response_json", (
            response["request_id"], response["role"], response["state"], canonical_json(response)))
        self.append(c, {
            **{k: response.get(k) for k in ("request_id", "role", "decision", "reason_code", "policy_version", "risk", "stage_timings", "state", "executed")},
            **metadata, "previous_state": previous, "reviewer_id": reviewer,
        })

    def fetch(self, c, request_id):
        return c.execute("SELECT g.*,a.state,a.response_json FROM governed_actions g JOIN actions a USING(request_id) WHERE request_id=?", (request_id,)).fetchone()

    def verify(self, checkpoint=None):
        with self.connection() as c:
            rows = c.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall()
        previous = GENESIS_HASH
        anchors = {0: previous}
        for index, row in enumerate(rows, 1):
            try:
                event = json.loads(row["event_json"])
                valid = (row["sequence"] == index and event["sequence"] == index and
                         event["request_id"] == row["request_id"] and event["role"] == row["role"] and
                         row["previous_hash"] == previous and
                         hashlib.sha256((previous + row["event_json"]).encode()).hexdigest() == row["event_hash"])
            except (ValueError, KeyError, TypeError):
                valid = False
            if not valid:
                return {"valid": False, "broken_at_sequence": row["sequence"]}
            previous = row["event_hash"]
            anchors[index] = previous
        if checkpoint is not None:
            exp_count = checkpoint.get("event_count")
            exp_head = checkpoint.get("head_hash")
            anchored = (
                isinstance(exp_count, int)
                and exp_count >= 0
                and isinstance(exp_head, str)
                and len(exp_head) == 64
                and anchors.get(exp_count) == exp_head
            )
        else:
            anchored = True
        return {"valid": anchored, "event_count": len(rows), "head_hash": previous,
                "checkpoint_matched": anchored if checkpoint is not None else None,
                "protection": "Tamper-evident, not immutable; retain checkpoints independently."}


if __name__ == "__main__":
    Store(Path(__file__).resolve().parent.parent / "data/governor.db").migrate()
    print("Governance schema is current; historical records preserved.")
