"""Private registry used only by Governor after a durable EXECUTING claim."""
import csv
import hashlib
import io
import json
import os
import sqlite3
from pathlib import Path
from uuid import uuid4
from core.audit_store import canonical_json
from core.governor_store import now
from core.governor_policy import SCHEMAS
from core.tool_executor import READ_QUERIES


def _formula_safe(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + value
    return value


class Adapters:
    def __init__(self, store, demo_path, report_dir):
        self.store, self.demo_path, self.report_dir = store, Path(demo_path), Path(report_dir)
        self._registry = {"database.read": self._read, "report.create": self._create, "report.send": self._send}

    def dispatch(self, request_id, action, principal, artifact):
        SCHEMAS[action.tool].model_validate(action.arguments)
        with self.store.connection() as c:
            row = self.store.fetch(c, request_id)
            if not row or row["state"] != "EXECUTING" or row["principal_id"] != principal.principal_id or json.loads(row["action_json"]) != action.model_dump():
                raise PermissionError("No matching durable execution claim")
        adapter = self._registry.get(action.tool)
        if adapter is None:
            raise PermissionError("Unknown adapter")
        return adapter(request_id, action, principal, artifact)

    def _artifact(self, artifact_id, action, principal, kind, content, data, source=None, sensitivity="internal"):
        with self.store.connection(True) as c:
            c.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)", (
                artifact_id, principal.principal_id, action.task_id, action.resource, kind, sensitivity,
                hashlib.sha256(content).hexdigest(), canonical_json(data), source, now()))
        return artifact_id

    def _read(self, request_id, action, principal, artifact):
        uri = self.demo_path.resolve().as_uri() + "?mode=ro"
        c = sqlite3.connect(uri, uri=True, timeout=2)
        try:
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA query_only=ON")
            rows = [dict(r) for r in c.execute(READ_QUERIES[action.resource], (action.arguments["limit"],)).fetchall()]
        finally:
            c.close()
        data = {"rows": rows}
        if len(canonical_json(data).encode()) > 65536:
            raise ValueError("Read output exceeds 64 KiB")
        aid = self._artifact(uuid4().hex, action, principal, "data", canonical_json(data).encode(), data)
        return {"resource": action.resource, "row_count": len(rows), "rows": rows, "artifact_id": aid}

    def _create(self, request_id, action, principal, artifact):
        data = json.loads(artifact["data_json"])
        if hashlib.sha256(canonical_json(data).encode()).hexdigest() != artifact["content_digest"]:
            raise ValueError("Source integrity failure")
        fmt = action.arguments["format"]
        if fmt == "json":
            content = canonical_json(data).encode()
        else:
            stream = io.StringIO(newline="")
            rows = data["rows"]
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["month", "total_sales"])
            writer.writeheader()
            writer.writerows({k: _formula_safe(v) for k, v in row.items()} for row in rows)
            content = stream.getvalue().encode("utf-8")
        aid = uuid4().hex
        self.report_dir.mkdir(parents=True, exist_ok=True)
        target = self.report_dir / (aid + "." + fmt)
        temp = self.report_dir / (aid + ".tmp")
        try:
            with temp.open("xb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, target)
            self._artifact(aid, action, principal, "report", content, {"rows": data["rows"], "filename": target.name}, artifact["artifact_id"], artifact["sensitivity"])
        finally:
            temp.unlink(missing_ok=True)
        return {"artifact_id": aid, "format": fmt, "content_digest": hashlib.sha256(content).hexdigest(), "row_count": len(data["rows"])}

    def _send(self, request_id, action, principal, artifact):
        # Filename is server generated and still checked at the filesystem boundary.
        filename = json.loads(artifact["data_json"])["filename"]
        if filename not in (artifact["artifact_id"] + ".csv", artifact["artifact_id"] + ".json"):
            raise PermissionError("Invalid report name")
        with (self.report_dir / filename).open("rb") as source:
            content = source.read(262145)
        if len(content) > 262144:
            raise ValueError("Report exceeds size limit")
        if hashlib.sha256(content).hexdigest() != artifact["content_digest"]:
            raise ValueError("Report integrity failure")
        with self.store.connection(True) as c:
            c.execute("INSERT OR IGNORE INTO outbox VALUES(?,?,?,?,?)", (
                request_id, artifact["artifact_id"], action.arguments["recipient"], "simulated", now()))
        return {"delivery_mode": "simulated", "outbox_id": request_id, "artifact_id": artifact["artifact_id"]}


