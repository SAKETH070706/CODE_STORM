"""Organization-aware four-tier orchestration, sharing the existing controlled primitives."""
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import time
from sqlalchemy import select
from fastapi import HTTPException
from core.permission_governor import ActionRequest
from core.governor_policy import SCHEMAS, load_policy
from core.governor_semantic import assess
from core.tool_executor import READ_QUERIES
from core.governor_adapters import _formula_safe
from core.audit_store import canonical_json
from workspace.models import Organization, Agent, Task, Connector, Policy, Action, Artifact, Approval, Outbox, Credential, Idempotency, owned, uid, listed, public
from workspace.rules import RuleSet, CAPABILITIES, matching
from workspace.identity import Identity, require
from workspace.audit import append, digest


class Runtime:
    def __init__(self, db, report_root, demo_db):
        self.db, self.report_root, self.demo_db = db, Path(report_root), Path(demo_db)

    def evaluate(self, s, identity, raw):
        result = {"decision": "BLOCK", "reason_code": "INVALID_ARGUMENTS", "reason": "Invalid action", "role": identity.role,
                  "executed": False, "result": None, "risk": None, "matched_rule_ids": [], "source_references": [], "reviewer_groups": [],
                  "policy_version": None, "policy_digest": None, "stage_timings": {}, "tiers": {"tier0": "BLOCK", "tier1": "SKIPPED", "tier2": "SKIPPED", "tier3": "PENDING"}}
        org = s.get(Organization, identity.organization_id)
        if org and org.active_policy_id:
            current_policy = owned(s, Policy, identity.organization_id, org.active_policy_id)
            result.update(policy_version=current_policy.id, policy_digest=current_policy.data.get("digest"))
        action, artifact, connector, context = None, None, None, None
        def deny(code):
            result.update(decision="BLOCK", reason_code=code, reason=code.replace("_", " ").lower())
            return result, action, artifact, connector, context
        if identity.kind != "agent":
            return deny("AGENT_IDENTITY_REQUIRED")
        try:
            action = ActionRequest.model_validate(raw)
            if action.tool not in SCHEMAS:
                return deny("TOOL_NOT_SUPPORTED")
            action.arguments = SCHEMAS[action.tool].model_validate(action.arguments).model_dump()
        except Exception:
            return deny("INVALID_ARGUMENTS")
        try:
            agent = owned(s, Agent, identity.organization_id, identity.principal_id)
            task = owned(s, Task, identity.organization_id, action.task_id)
            connector = owned(s, Connector, identity.organization_id, action.resource)
        except HTTPException:
            return deny("SCOPE_DENIED")
        if agent.state != "ACTIVE" or agent.data["role"] != identity.role:
            return deny("AGENT_REVOKED_OR_CHANGED")
        if identity.credential_id:
            credential = s.get(Credential, identity.credential_id)
            if not credential or not credential.active or credential.agent_id != agent.id or credential.organization_id != identity.organization_id:
                return deny("CREDENTIAL_REVOKED")
        if task.state != "ACTIVE" or agent.id not in task.data["agents"] or identity.role not in task.data["roles"] or connector.id not in task.data["resources"]:
            return deny("TASK_DENIED")
        if connector.state != "ACTIVE" or action.tool not in CAPABILITIES.get(connector.data["kind"], set()):
            return deny("CAPABILITY_DENIED")
        if action.tool != "database.read":
            aid = action.arguments.get("source_artifact_id") or action.arguments.get("artifact_id")
            try:
                artifact = owned(s, Artifact, identity.organization_id, aid)
            except HTTPException:
                return deny("ARTIFACT_DENIED")
            if artifact.state != "ACTIVE":
                return deny("LEGACY_ARTIFACT_REQUIRES_NEW_READ")
            expected = "data" if action.tool == "report.create" else "report"
            if artifact.data["principal_id"] != agent.id or artifact.data["task_id"] != task.id or artifact.data["kind"] != expected:
                return deny("ARTIFACT_DENIED")
        if action.tool == "report.send":
            if action.arguments["recipient"] not in connector.data["destinations"] or artifact.data["sensitivity"] != "internal":
                return deny("EXPORT_DENIED")
        org = s.get(Organization, identity.organization_id)
        if not org.active_policy_id:
            return deny("NO_PUBLISHED_POLICY")
        policy = owned(s, Policy, identity.organization_id, org.active_policy_id)
        if policy.state != "PUBLISHED" or digest(policy.data["rules"]) != policy.data["digest"]:
            return deny("POLICY_INTEGRITY_FAILURE")
        rules = RuleSet.model_validate({"rules": policy.data["rules"]}).rules
        decision, matches = matching(rules, identity.role, action.model_dump())
        result.update(policy_version=policy.id, policy_digest=policy.data["digest"], matched_rule_ids=[r.id for r in matches],
                      source_references=[r.source.model_dump() for r in matches], reviewer_groups=sorted({r.reviewer_group for r in matches if r.decision == "ESCALATE"}))
        if decision == "BLOCK":
            return deny("POLICY_BLOCK" if matches else "DEFAULT_DENY")
        result["tiers"]["tier0"] = "PASS"
        risk_policy = load_policy()
        recent = list(s.scalars(select(Action).where(Action.organization_id == identity.organization_id, Action.name == agent.id).order_by(Action.created_at.desc()).limit(10)))
        factors = {"impact": {"database.read": 0, "report.create": .25, "report.send": .75}[action.tool],
                   "sensitivity": .25 if not artifact or artifact.data["sensitivity"] == "internal" else 1,
                   "blast_radius": action.arguments.get("limit", 10) / 100 if not artifact else min(len(artifact.data.get("rows", [])) / 100, 1),
                   "external_egress": 1 if action.tool == "report.send" else 0, "provenance_uncertainty": 0,
                   "recent_denials": sum(r.state == "BLOCKED" for r in recent) / 10}
        score = round(sum(risk_policy.weights[k] * v for k, v in factors.items()), 2)
        category = "Low"
        for name in ("medium", "high", "critical"):
            if score >= risk_policy.thresholds[name]:
                category = name.title()
        result["risk"] = {"score": score, "category": category, "factors": factors, "explanation": "Versioned initial risk weights; server provenance and measured last-ten denial count. Not probabilities."}
        result["tiers"]["tier1"] = category
        if score >= risk_policy.thresholds["critical"]:
            return deny("CRITICAL_RISK")
        if score >= risk_policy.thresholds["medium"]:
            decision = "ESCALATE"
        if decision == "ESCALATE" and not result["reviewer_groups"]:
            # Risk escalation without a configured review route cannot execute.
            return deny("REVIEW_ROUTE_MISSING")
        context = digest({"policy": policy.data["digest"], "policy_id": policy.id, "risk_policy": risk_policy.model_dump(),
                          "task": task.data, "agent": agent.data, "connector": connector.data, "artifact": artifact.data if artifact else None})
        result.update(decision=decision, reason_code="AUTHORIZED" if decision == "ALLOW" else "HUMAN_REVIEW_REQUIRED", reason="Published rules and current context evaluated")
        return result, action, artifact, connector, context

    def event(self, s, identity, row, previous=None):
        response = row.data["response"]
        append(s, row.organization_id, identity.principal_id, "action.transition", {
            "request_id": row.id, "agent_id": row.name, "state": row.state, "previous_state": previous,
            **{k: response.get(k) for k in ("decision", "reason_code", "policy_version", "policy_digest", "matched_rule_ids", "risk", "stage_timings", "source_references")},
            "action_digest": row.data["action_digest"], "reviewer_id": row.data.get("reviewer_id")})

    def change(self, s, identity, row, state, **updates):
        previous = row.state
        row.state = state
        row.data = {**row.data, "response": {**row.data["response"], **updates, "state": state,
                    "tiers": {**row.data["response"].get("tiers", {}), "tier3": state}}}
        self.event(s, identity, row, previous)
        return row.data["response"]

    def submit(self, identity, raw, key=None, evaluation_only=False, initiated_by=None):
        rid = uid()
        try:
            return self._submit(identity, raw, key, evaluation_only, initiated_by, rid)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, {"request_id": rid, "state": "PERSISTENCE_UNAVAILABLE", "message": "Pre-execution work failed; this submission did not dispatch."})

    def _submit(self, identity, raw, key, evaluation_only, initiated_by, rid):
        started = time.perf_counter()
        if key is not None and (not 1 <= len(key) <= 128 or not key.isascii()):
            raise HTTPException(400, "Invalid idempotency key")
        if identity.legacy_demo:
            with self.db.transaction(identity.organization_id) as s:
                raw = dict(raw)
                task = next((t for t in listed(s, Task, identity.organization_id) if t.data.get("legacy_task") == raw.get("task_id")), None)
                resource_name = "delivery" if raw.get("tool") == "report.send" and raw.get("resource") == "sales_report" else raw.get("resource")
                connector = next((c for c in listed(s, Connector, identity.organization_id) if c.data.get("legacy_resource") == resource_name), None)
                if task: raw["task_id"] = task.id
                if connector: raw["resource"] = connector.id
        payload_digest = digest({"payload": raw, "evaluation_only": evaluation_only})
        with self.db.transaction(identity.organization_id) as s:
            result, action, artifact, connector, context = self.evaluate(s, identity, raw)
        result["stage_timings"]["tier0_1_ms"] = round((time.perf_counter() - started) * 1000, 3)
        semantic_start = time.perf_counter()
        risk_policy = load_policy()
        if result["decision"] != "BLOCK" and result["risk"]["score"] >= risk_policy.semantic_required_at:
            assessment = assess(action, result["risk"]) if risk_policy.semantic_enabled else None
            result["tiers"]["tier2"] = assessment.verdict if assessment else "UNAVAILABLE"
            if assessment is None:
                result["decision"] = risk_policy.semantic_unavailable
                result["reason_code"] = "SEMANTIC_UNAVAILABLE"
            elif assessment.verdict != "ALLOW":
                result["decision"] = assessment.verdict
            if result["decision"] == "ESCALATE" and not result["reviewer_groups"]:
                result.update(decision="BLOCK", reason_code="REVIEW_ROUTE_MISSING")
        result["stage_timings"]["tier2_ms"] = round((time.perf_counter() - semantic_start) * 1000, 3)
        with self.db.transaction(identity.organization_id) as s:
            if key:
                existing = s.scalar(select(Idempotency).where(Idempotency.organization_id == identity.organization_id, Idempotency.principal_id == identity.principal_id, Idempotency.key == key))
                if existing:
                    if existing.payload_digest != payload_digest:
                        raise HTTPException(409, "Idempotency payload conflict")
                    return owned(s, Action, identity.organization_id, existing.action_id).data["response"]
            fresh, _, _, _, fresh_context = self.evaluate(s, identity, raw)
            if result["decision"] != "BLOCK" and (fresh["decision"] == "BLOCK" or fresh_context != context or (fresh["risk"] and fresh["risk"]["score"] > result["risk"]["score"])):
                result.update(decision="BLOCK", reason_code="CONTEXT_CHANGED")
            state = {"ALLOW": "AUTHORIZED", "ESCALATE": "REVIEW_REQUIRED", "BLOCK": "BLOCKED"}[result["decision"]]
            if evaluation_only:
                state = "EVALUATED" if result["decision"] == "ALLOW" else state
            normalized = action.model_dump() if action else raw
            adigest = digest({"action": normalized, "principal": identity.principal_id, "organization": identity.organization_id,
                              "policy": result["policy_digest"], "context": context})
            result["tiers"]["tier3"] = state
            result.update(request_id=rid, state=state, processing_ms=round((time.perf_counter()-started)*1000, 3))
            row = Action(id=rid, organization_id=identity.organization_id, name=identity.principal_id, state=state, data={
                "action": normalized if state != "BLOCKED" else {}, "action_digest": adigest, "context_digest": context,
                "response": result, "expires_at": time.time() + risk_policy.approval_seconds, "evaluation_only": evaluation_only,
                "credential_id": identity.credential_id, "initiated_by": initiated_by, "role": identity.role})
            s.add(row); s.flush()
            if key:
                s.add(Idempotency(organization_id=identity.organization_id, principal_id=identity.principal_id, key=key, payload_digest=payload_digest, action_id=rid))
            self.event(s, identity, row)
        if state == "AUTHORIZED":
            return self.execute(identity, rid)
        return result

    def execute(self, identity, rid):
        with self.db.transaction(identity.organization_id) as s:
            row = owned(s, Action, identity.organization_id, rid)
            if row.state not in {"AUTHORIZED", "REVALIDATING"} or row.data["evaluation_only"]:
                return row.data["response"]
            fresh, action, artifact, connector, context = self.evaluate(s, identity, row.data["action"])
            if time.time() >= row.data["expires_at"]:
                return self.change(s, identity, row, "EXPIRED", decision="BLOCK", reason_code="EXPIRED")
            bound = digest({"action": row.data["action"], "principal": row.name, "organization": identity.organization_id,
                            "policy": fresh["policy_digest"], "context": context})
            if fresh["decision"] == "BLOCK" or context != row.data["context_digest"] or bound != row.data["action_digest"]:
                return self.change(s, identity, row, "BLOCKED", decision="BLOCK", reason_code="REVALIDATION_FAILED")
            approved = s.get(Approval, rid)
            if approved and (approved.organization_id != identity.organization_id or approved.data["action_digest"] != bound or fresh["risk"]["score"] > row.data["response"]["risk"]["score"]):
                return self.change(s, identity, row, "BLOCKED", decision="BLOCK", reason_code="APPROVAL_BINDING_CHANGED")
            if fresh["decision"] == "ESCALATE" and not approved:
                return self.change(s, identity, row, "REVIEW_REQUIRED", decision="ESCALATE")
            if row.state == "REVALIDATING":
                self.change(s, identity, row, "AUTHORIZED", decision="ALLOW", reason_code="REVIEW_APPROVED")
            self.change(s, identity, row, "EXECUTING")
            response = dict(row.data["response"])
            source_data = artifact.data if artifact else None
            connector_data = dict(connector.data)
        # Only this durable claim reaches adapter work. No externally exposed dispatch API.
        start = time.perf_counter()
        new_artifact, outbox = None, None
        try:
            result, new_artifact, outbox = self._adapter(identity, rid, action, connector_data, source_data)
            state, executed = "SUCCEEDED", True
        except (ValueError, FileNotFoundError, PermissionError):
            result, state, executed = None, "FAILED", False
        except Exception:
            result, state, executed = None, "OUTCOME_UNKNOWN", None
        response.update(state=state, executed=executed, result=result)
        response["tiers"] = {**response["tiers"], "tier3": state}
        response["stage_timings"] = {**response["stage_timings"], "execution_ms": round((time.perf_counter()-start)*1000, 3)}
        try:
            with self.db.transaction(identity.organization_id) as s:
                row = owned(s, Action, identity.organization_id, rid)
                if new_artifact:
                    s.add(new_artifact)
                if outbox:
                    s.add(outbox)
                row.data = {**row.data, "response": response}
                self.change(s, identity, row, state)
        except Exception:
            response.update(state="OUTCOME_UNKNOWN", executed=None, result=None, reason_code="OUTCOME_PERSISTENCE_FAILED")
        return response

    def _adapter(self, identity, rid, action, connector, source):
        aid = uid()
        common = {"principal_id": identity.principal_id, "task_id": action.task_id, "resource": action.resource, "sensitivity": "internal"}
        if action.tool == "database.read":
            resource = {"demo_sales": "sales_summary", "demo_support": "support_summary"}[connector["kind"]]
            c = sqlite3.connect(self.demo_db.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
            try:
                c.row_factory = sqlite3.Row; c.execute("PRAGMA query_only=ON")
                rows = [dict(r) for r in c.execute(READ_QUERIES[resource], (action.arguments["limit"],))]
            finally:
                c.close()
            encoded = canonical_json({"rows": rows}).encode()
            if len(encoded) > 65536:
                raise ValueError("Read output too large")
            data = {**common, "kind": "data", "rows": rows, "content_digest": digest({"rows": rows})}
            artifact = Artifact(id=aid, organization_id=identity.organization_id, data=data)
            return {"rows": rows, "row_count": len(rows), "artifact_id": aid}, artifact, None
        folder = self.report_root / identity.organization_id
        if action.tool == "report.create":
            if digest({"rows": source["rows"]}) != source["content_digest"]:
                raise ValueError("Source integrity failure")
            rows = source["rows"]
            if action.arguments["format"] == "json":
                content = canonical_json({"rows": rows}).encode()
            else:
                buffer = io.StringIO(newline="")
                writer = csv.DictWriter(buffer, fieldnames=list(rows[0]) if rows else ["empty"])
                writer.writeheader(); writer.writerows({k: _formula_safe(v) for k,v in r.items()} for r in rows)
                content = buffer.getvalue().encode()
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            name = aid + "." + action.arguments["format"]
            temporary = folder / (aid + ".tmp")
            with temporary.open("xb") as f:
                f.write(content); f.flush(); os.fsync(f.fileno())
            os.replace(temporary, folder / name)
            import hashlib
            data = {**common, "kind": "report", "rows": rows, "sensitivity": source["sensitivity"], "filename": name,
                    "source_id": action.arguments["source_artifact_id"], "content_digest": hashlib.sha256(content).hexdigest()}
            return {"artifact_id": aid, "format": action.arguments["format"], "content_digest": data["content_digest"]}, Artifact(id=aid, organization_id=identity.organization_id, data=data), None
        if action.tool == "report.send":
            import hashlib
            name = source["filename"]
            artifact_id = action.arguments["artifact_id"]
            if name not in (artifact_id + ".csv", artifact_id + ".json"):
                raise PermissionError("Invalid artifact filename")
            with (folder / name).open("rb") as f:
                content = f.read(262145)
            if len(content) > 262144 or hashlib.sha256(content).hexdigest() != source["content_digest"]:
                raise ValueError("Report integrity failure")
            data = {"artifact_id": artifact_id, "destination": action.arguments["recipient"], "delivery_mode": "simulated"}
            return {**data, "outbox_id": rid}, None, Outbox(id=rid, organization_id=identity.organization_id, data=data)
        raise PermissionError("Unsupported adapter")

    def review(self, reviewer, rid, approved, comment):
        require(reviewer, "review")
        with self.db.transaction(reviewer.organization_id) as s:
            row = owned(s, Action, reviewer.organization_id, rid)
            if row.name == reviewer.principal_id or row.data.get("initiated_by") == reviewer.principal_id:
                raise HTTPException(403, "You cannot approve your own action")
            if not set(row.data["response"]["reviewer_groups"]) <= reviewer.groups:
                raise HTTPException(403, "Required reviewer group membership missing")
            if row.state != "REVIEW_REQUIRED" or row.data["evaluation_only"]:
                raise HTTPException(409, "Action is not pending review")
            if time.time() >= row.data["expires_at"]:
                return self.change(s, reviewer, row, "EXPIRED", decision="BLOCK", reason_code="EXPIRED")
            s.add(Approval(id=rid, organization_id=reviewer.organization_id, state="APPROVED" if approved else "REJECTED", data={
                "reviewer_id": reviewer.principal_id, "comment": comment, "action_digest": row.data["action_digest"], "decision_time": time.time()}))
            row.data = {**row.data, "reviewer_id": reviewer.principal_id}
            if not approved:
                return self.change(s, reviewer, row, "REJECTED", decision="BLOCK", reason_code="REVIEW_REJECTED")
            self.change(s, reviewer, row, "APPROVED")
            self.change(s, reviewer, row, "REVALIDATING")
            owner = Identity(row.name, row.organization_id, "agent", row.data["role"], credential_id=row.data.get("credential_id"))
        return self.execute(owner, rid)

    def status(self, identity, rid):
        with self.db.transaction(identity.organization_id) as s:
            row = owned(s, Action, identity.organization_id, rid)
            if identity.kind == "agent" and row.name != identity.principal_id:
                raise HTTPException(404, "Action not found")
            if identity.kind == "human" and not ({"activity", "review", "audit"} & identity.permissions):
                raise HTTPException(403, "Action read permission required")
            if row.state == "REVIEW_REQUIRED" and time.time() >= row.data["expires_at"]:
                self.change(s, identity, row, "EXPIRED", decision="BLOCK", reason_code="EXPIRED")
            artifact_id = row.data["action"].get("arguments", {}).get("artifact_id") or row.data["action"].get("arguments", {}).get("source_artifact_id")
            artifact = s.get(Artifact, artifact_id) if artifact_id else None
            sensitivity = artifact.data.get("sensitivity") if artifact and artifact.organization_id == identity.organization_id else None
            result = {"artifact_sensitivity": sensitivity, **row.data["response"], "action": row.data["action"], "action_digest": row.data["action_digest"], "agent_id": row.name,
                      "expires_at": row.data["expires_at"], "initiated_by": row.data.get("initiated_by")}
            approval = s.get(Approval, rid)
            if approval and approval.organization_id == identity.organization_id:
                result["approval"] = approval.data
            return result

