"""Orchestrates authorization, durable decisions, review and controlled dispatch."""
import json
import sqlite3
import time
from uuid import uuid4
from fastapi import HTTPException
from core.audit_store import canonical_json
from core.governor_identity import Principal, require
from core.governor_policy import evaluate, load_policy, SCHEMAS, TASK_POLICIES, ROLE_PERMISSIONS
from core.governor_semantic import assess
from core.governor_store import digest, now


class Governor:
    def __init__(self, store, adapters, policy_path=None):
        self.store, self.adapters, self.policy_path = store, adapters, policy_path

    def metadata(self, raw, principal_id, action_digest):
        allowed = {
            "task_id": set(TASK_POLICIES), "tool": set(SCHEMAS),
            "resource": {r for tools in ROLE_PERMISSIONS.values() for resources in tools.values() for r in resources},
        }
        return {"principal_id": principal_id, "action_digest": action_digest,
                **{key: raw.get(key) if isinstance(raw.get(key), str) and raw[key] in values else "[unsupported]"
                   for key, values in allowed.items()}}
    def _semantic(self, response, action, policy):
        started = time.perf_counter()
        risk = response.get("risk")
        if response["decision"] != "BLOCK" and risk and risk["score"] >= policy.semantic_required_at:
            result = assess(action, risk) if policy.semantic_enabled else None
            if result is None:
                response.update(decision=policy.semantic_unavailable, reason_code="SEMANTIC_UNAVAILABLE", reason="Required semantic assessment unavailable; applying configured fallback.")
            elif result.verdict != "ALLOW":
                response.update(decision=result.verdict, reason_code="SEMANTIC_REVIEW", reason="Semantic assessment recommends additional restriction.")
        response["stage_timings"]["semantic_ms"] = round((time.perf_counter() - started) * 1000, 3)

    def submit(self, raw, principal, key=None, evaluation_only=False):
        rid = str(uuid4())
        try:
            return self._submit(raw, principal, key, evaluation_only, rid)
        except sqlite3.Error:
            raise HTTPException(503, {"request_id": rid, "state": "PERSISTENCE_UNAVAILABLE",
                                      "message": "Mandatory persistence failed; this request did not dispatch."})

    def _submit(self, raw, principal, key, evaluation_only, rid):
        started = time.perf_counter()
        policy = load_policy(self.policy_path)
        payload_digest = digest({"payload": raw, "evaluation_only": evaluation_only})
        if key is not None and (not isinstance(key, str) or not 1 <= len(key) <= 128 or not key.isascii()):
            raise HTTPException(400, "Invalid idempotency key")
        with self.store.connection() as c:
            response, action, artifact, context = evaluate(c, raw, principal, policy)
        response["stage_timings"]["deterministic_ms"] = round((time.perf_counter() - started) * 1000, 3)
        self._semantic(response, action, policy)
        normalized = action.model_dump() if action and response["reason_code"] != "INVALID_ARGUMENTS" else raw
        # Invalid payloads are hashed, not retained verbatim (may contain credentials).
        persisted_action = normalized if response["decision"] != "BLOCK" else {k: self.metadata(normalized, principal.principal_id, "").get(k) for k in ("task_id", "tool", "resource")}
        adigest = digest({"action": normalized, "principal_id": principal.principal_id, "role": principal.role, "policy": policy.model_dump()})
        response.update(request_id=rid, state={"ALLOW": "AUTHORIZED", "BLOCK": "BLOCKED", "ESCALATE": "REVIEW_REQUIRED"}[response["decision"]], processing_ms=0)
        if evaluation_only and response["decision"] == "ALLOW":
            response["state"] = "EVALUATED"
        metadata = self.metadata(normalized, principal.principal_id, adigest)
        with self.store.connection(True) as c:
            if key:
                existing = c.execute("SELECT * FROM idempotency WHERE principal_id=? AND key=?", (principal.principal_id, key)).fetchone()
                if existing:
                    if existing["payload_digest"] != payload_digest:
                        self.store.append(c, {**metadata, "request_id": existing["request_id"], "role": principal.role,
                                              "decision": "BLOCK", "reason_code": "IDEMPOTENCY_CONFLICT", "policy_version": policy.version})
                        # Commit the denial before raising the conflict.
                        c.commit()
                        raise HTTPException(409, "Idempotency key already binds a different payload")
                    return json.loads(self.store.fetch(c, existing["request_id"])["response_json"])
            # Detect policy/assignment/artifact changes during semantic evaluation.
            current = load_policy(self.policy_path)
            fresh, _, _, fresh_context = evaluate(c, raw, principal, current)
            if response["decision"] != "BLOCK" and (fresh["decision"] == "BLOCK" or context != fresh_context or current != policy):
                response.update(decision="BLOCK", state="BLOCKED", reason_code="CONTEXT_CHANGED", reason="Authorization context changed; submit a fresh action.")
            response["processing_ms"] = round((time.perf_counter() - started) * 1000, 3)
            response["stage_timings"]["precommit_ms"] = response["processing_ms"]
            self.store.save(c, response, metadata)
            c.execute("INSERT INTO governed_actions VALUES(?,?,?,?,?,?,?,?,?)", (
                rid, principal.principal_id, canonical_json(persisted_action), adigest, policy.version,
                context, now(), time.time() + policy.approval_seconds, int(evaluation_only)))
            if key:
                c.execute("INSERT INTO idempotency VALUES(?,?,?,?)", (principal.principal_id, key, payload_digest, rid))
        if response["decision"] == "ALLOW" and not evaluation_only:
            return self._execute(rid, principal)
        return response

    def _transition(self, c, row, state, reviewer=None, **updates):
        response = json.loads(row["response_json"])
        response.update(state=state, **updates)
        raw = json.loads(row["action_json"])
        self.store.save(c, response, self.metadata(raw, row["principal_id"], row["action_digest"]), row["state"], reviewer)
        return response

    def _execute(self, rid, principal):
        # BEGIN IMMEDIATE serializes competing claims; only AUTHORIZED can dispatch.
        with self.store.connection(True) as c:
            row = self.store.fetch(c, rid)
            if row["state"] not in {"AUTHORIZED", "REVALIDATING"} or row["evaluation_only"]:
                return json.loads(row["response_json"])
            policy = load_policy(self.policy_path)
            raw = json.loads(row["action_json"])
            fresh, action, artifact, context = evaluate(c, raw, principal, policy)
            bound = digest({"action": raw, "principal_id": principal.principal_id, "role": principal.role, "policy": policy.model_dump()})
            approval = c.execute("SELECT * FROM approvals WHERE request_id=? AND decision='APPROVED'", (rid,)).fetchone()
            if time.time() >= row["expires_at"]:
                return self._transition(c, row, "EXPIRED", decision="BLOCK", reason_code="APPROVAL_EXPIRED")
            if fresh["decision"] == "BLOCK" or context != row["context_digest"] or bound != row["action_digest"] or (approval and approval["action_digest"] != bound):
                return self._transition(c, row, "BLOCKED", decision="BLOCK", reason_code="REVALIDATION_FAILED", reason="Policy, action or context changed; submit again.")
            previous_risk = json.loads(row["response_json"]).get("risk") or {}
            if approval and fresh["risk"]["score"] > previous_risk.get("score", 0):
                return self._transition(c, row, "BLOCKED", decision="BLOCK", reason_code="CONTEXT_CHANGED", reason="Risk increased after review; submit a fresh action.")
            if fresh["decision"] == "ESCALATE" and not approval:
                return self._transition(c, row, "REVIEW_REQUIRED", decision="ESCALATE", reason_code="HUMAN_REVIEW_REQUIRED")
            if row["state"] == "REVALIDATING":
                self._transition(c, row, "AUTHORIZED", approval["reviewer_id"], decision="ALLOW", reason_code="REVIEW_APPROVED", reason="Reviewed action passed current authorization and context checks.")
                row = self.store.fetch(c, rid)
            response = self._transition(c, row, "EXECUTING")
        started = time.perf_counter()
        try:
            result = self.adapters.dispatch(rid, action, principal, artifact)
            response.update(state="SUCCEEDED", result=result, executed=True)
        except (FileNotFoundError, PermissionError, ValueError):
            response.update(state="FAILED", executed=False, reason_code="ADAPTER_REJECTED", reason="Adapter validation or required source failed before side effects.")
        except Exception:
            # An adapter can have persisted a file/outbox before its exception.
            response.update(state="OUTCOME_UNKNOWN", executed=None, reason_code="EXECUTION_UNCERTAIN", reason="Dispatch was attempted. Do not blindly replay.")
        response["stage_timings"]["execution_ms"] = round((time.perf_counter() - started) * 1000, 3)
        response["processing_ms"] += response["stage_timings"]["execution_ms"]
        try:
            with self.store.connection(True) as c:
                row = self.store.fetch(c, rid)
                self.store.save(c, response, self.metadata(action.model_dump(), principal.principal_id, row["action_digest"]), "EXECUTING")
        except Exception:
            response.update(state="OUTCOME_UNKNOWN", executed=None, reason_code="OUTCOME_PERSISTENCE_FAILED", reason="Dispatch was attempted but its outcome could not be committed; use this request ID for reconciliation.", result=None)
        return response

    def status(self, rid, principal, review=False):
        if review:
            require(principal, "review")
        with self.store.connection(True) as c:
            row = self.store.fetch(c, rid)
            if not row or (row["principal_id"] != principal.principal_id and not (review and "review" in principal.permissions)):
                raise HTTPException(404, "Action not found")
            if row["state"] in ("REVIEW_REQUIRED", "APPROVED", "AUTHORIZED") and time.time() >= row["expires_at"]:
                self._transition(c, row, "EXPIRED", decision="BLOCK", reason_code="APPROVAL_EXPIRED")
                row = self.store.fetch(c, rid)
            response = json.loads(row["response_json"])
            if review:
                raw = json.loads(row["action_json"])
                args = raw.get("arguments", {})
                response.update(principal_id=row["principal_id"], action_digest=row["action_digest"], created_at=row["created_at"], expires_at=row["expires_at"],
                                task=raw.get("task_id"), tool=raw.get("tool"), resource=raw.get("resource"),
                                arguments={k: v for k, v in args.items() if k in {"limit", "format", "artifact_id", "source_artifact_id", "report_id"}})
                if "recipient" in args:
                    response["arguments"]["recipient"] = "[allowlisted destination]"
                approval = c.execute("SELECT reviewer_id,decision,comment,decided_at FROM approvals WHERE request_id=?", (rid,)).fetchone()
                response["review"] = dict(approval) if approval else None
            return response

    def list_reviews(self, principal, limit: int = 50):
        require(principal, "review")
        now_ts = time.time()
        with self.store.connection(False) as c:
            candidates = c.execute(
                "SELECT a.request_id, a.state, g.expires_at "
                "FROM actions a JOIN governed_actions g USING(request_id) "
                "WHERE a.state='REVIEW_REQUIRED' AND g.evaluation_only=0 "
                "ORDER BY g.created_at LIMIT ?",
                (limit,)
            ).fetchall()

        expired_ids = [r["request_id"] for r in candidates if now_ts >= r["expires_at"]]
        if expired_ids:
            with self.store.connection(True) as c:
                for rid in expired_ids:
                    row = self.store.fetch(c, rid)
                    if row and row["state"] in ("REVIEW_REQUIRED", "APPROVED", "AUTHORIZED") and time.time() >= row["expires_at"]:
                        self._transition(c, row, "EXPIRED", decision="BLOCK", reason_code="APPROVAL_EXPIRED")

        results = []
        with self.store.connection(False) as c:
            rows = c.execute(
                "SELECT a.request_id, a.state, a.response_json, g.action_json, g.principal_id, g.action_digest, g.created_at, g.expires_at "
                "FROM actions a JOIN governed_actions g USING(request_id) "
                "WHERE a.state='REVIEW_REQUIRED' AND g.evaluation_only=0 AND g.expires_at > ? "
                "ORDER BY g.created_at LIMIT ?",
                (now_ts, limit)
            ).fetchall()
            for row in rows:
                rid = row["request_id"]
                resp = json.loads(row["response_json"])
                raw = json.loads(row["action_json"])
                args = raw.get("arguments", {})
                resp.update(
                    principal_id=row["principal_id"], action_digest=row["action_digest"], created_at=row["created_at"], expires_at=row["expires_at"],
                    task=raw.get("task_id"), tool=raw.get("tool"), resource=raw.get("resource"),
                    arguments={k: v for k, v in args.items() if k in {"limit", "format", "artifact_id", "source_artifact_id", "report_id"}}
                )
                if "recipient" in args:
                    resp["arguments"]["recipient"] = "[allowlisted destination]"
                approval = c.execute("SELECT reviewer_id,decision,comment,decided_at FROM approvals WHERE request_id=?", (rid,)).fetchone()
                resp["review"] = dict(approval) if approval else None
                results.append(resp)
        return results

    def review(self, rid, reviewer, decision, comment=""):
        require(reviewer, "review")
        if decision not in {"APPROVED", "REJECTED"} or not isinstance(comment, str) or len(comment) > 500:
            raise HTTPException(400, "Invalid review decision")
        with self.store.connection(True) as c:
            row = self.store.fetch(c, rid)
            if not row:
                raise HTTPException(404, "Action not found")
            if row["principal_id"] == reviewer.principal_id:
                raise HTTPException(403, "Self approval is forbidden")
            if row["state"] != "REVIEW_REQUIRED" or row["evaluation_only"]:
                raise HTTPException(409, "Action is not eligible for review")
            if time.time() >= row["expires_at"]:
                return self._transition(c, row, "EXPIRED", reviewer.principal_id, decision="BLOCK", reason_code="APPROVAL_EXPIRED")
            c.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?)", (rid, reviewer.principal_id, decision, comment, now(), row["action_digest"]))
            state = "APPROVED" if decision == "APPROVED" else "REJECTED"
            response = self._transition(c, row, state, reviewer.principal_id, **({"decision": "BLOCK", "reason_code": "REVIEW_REJECTED", "reason": "Reviewer rejected the action."} if decision == "REJECTED" else {}))
            if decision != "APPROVED":
                return response
            row = self.store.fetch(c, rid)
            self._transition(c, row, "REVALIDATING", reviewer.principal_id)
            row = self.store.fetch(c, rid)
            owner = Principal(row["principal_id"], response["role"])
        return self._execute(rid, owner)

    def cancel(self, rid, principal):
        with self.store.connection(True) as c:
            row = self.store.fetch(c, rid)
            if not row or row["principal_id"] != principal.principal_id:
                raise HTTPException(404, "Action not found")
            if row["state"] not in ("REVIEW_REQUIRED", "APPROVED", "AUTHORIZED"):
                raise HTTPException(409, "Action cannot be cancelled")
            return self._transition(c, row, "CANCELLED", decision="BLOCK", reason_code="CANCELLED")

    def recover(self):
        """Run once at startup with exclusive process ownership, never during live dispatch."""
        with self.store.connection(True) as c:
            ids = c.execute("SELECT request_id FROM actions WHERE state IN ('EXECUTING','AUTHORIZED','APPROVED','REVALIDATING') AND request_id IN (SELECT request_id FROM governed_actions WHERE evaluation_only=0)").fetchall()
            for entry in ids:
                row = self.store.fetch(c, entry[0])
                self._transition(c, row, "OUTCOME_UNKNOWN", executed=None, reason_code="INTERRUPTED", reason="Previous process interrupted; reconcile before resubmission.")
