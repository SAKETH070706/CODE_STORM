"""Strict tool schemas and versioned deterministic context assessment."""
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from core.permission_governor import ActionRequest, ReadArguments, ROLE_PERMISSIONS, TASK_POLICIES
from core.governor_store import digest

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class CreateArguments(Strict):
    source_artifact_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    report_id: Literal["monthly-sales"] = "monthly-sales"
    format: Literal["csv", "json"] = "csv"

class SendArguments(Strict):
    artifact_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    report_id: Literal["monthly-sales"] = "monthly-sales"
    recipient: str = Field(min_length=3, max_length=100)

SCHEMAS = {"database.read": ReadArguments, "report.create": CreateArguments, "report.send": SendArguments}

class Policy(Strict):
    version: str = Field(min_length=1, max_length=80)
    weights: dict[str, int]
    thresholds: dict[str, int]
    approval_seconds: int = Field(ge=1, le=86400)
    destinations: list[str] = Field(min_length=1, max_length=20)
    export_sensitivities: list[Literal["internal", "confidential"]]
    semantic_enabled: bool
    semantic_required_at: int = Field(ge=1, le=100)
    semantic_unavailable: Literal["BLOCK", "ESCALATE"]


def load_policy(path=None):
    p = Policy.model_validate_json(Path(path or Path(__file__).resolve().parent.parent / "governor_policy.json").read_text(encoding="utf-8-sig"))
    expected = {"impact", "sensitivity", "blast_radius", "external_egress", "provenance_uncertainty", "recent_denials"}
    if set(p.weights) != expected or sum(p.weights.values()) != 100 or any(v < 0 for v in p.weights.values()):
        raise ValueError("Invalid risk weights")
    if set(p.thresholds) != {"medium", "high", "critical"} or not (0 < p.thresholds["medium"] < p.thresholds["high"] < p.thresholds["critical"] <= 100):
        raise ValueError("Invalid risk thresholds")
    return p


def evaluate(c, raw, principal, policy):
    """Hard denials return before risk/semantic assessment. No client trust labels."""
    base = {"decision": "BLOCK", "reason_code": "INVALID_ARGUMENTS", "reason": "Invalid action or arguments.",
            "role": principal.role, "policy_version": policy.version, "executed": False,
            "risk": None, "result": None, "stage_timings": {}}
    action = None
    artifact = None
    def deny(code, reason):
        base.update(reason_code=code, reason=reason)
        return base, action, artifact, ""
    try:
        action = ActionRequest.model_validate(raw)
    except Exception:
        return deny("INVALID_ARGUMENTS", "Use the strict action schema; identity and provenance are server controlled.")
    if action.tool not in SCHEMAS:
        return deny("TOOL_NOT_SUPPORTED", "Tool is not registered.")
    if action.resource not in ROLE_PERMISSIONS.get(principal.role, {}).get(action.tool, set()):
        return deny("ROLE_RESOURCE_DENIED", "Role cannot access this tool/resource.")
    assigned = c.execute("SELECT 1 FROM task_assignments WHERE principal_id=? AND role=? AND task_id=? AND active=1", (principal.principal_id, principal.role, action.task_id)).fetchone()
    task = TASK_POLICIES.get(action.task_id)
    if not assigned or not task or principal.role not in task["roles"]:
        return deny("TASK_DENIED", "Task is not assigned to this principal.")
    if action.tool not in task["tools"] or action.resource not in task["resources"]:
        return deny("TASK_SCOPE_DENIED", "Action exceeds task scope.")
    try:
        args = SCHEMAS[action.tool].model_validate(action.arguments)
        action.arguments = args.model_dump()
    except Exception:
        return deny("INVALID_ARGUMENTS", "Unsupported fields or argument values.")
    if action.tool != "database.read":
        artifact_id = getattr(args, "source_artifact_id", None) or getattr(args, "artifact_id", None)
        row = c.execute("SELECT * FROM artifacts WHERE artifact_id=? AND principal_id=? AND task_id=?", (artifact_id, principal.principal_id, action.task_id)).fetchone()
        if not row:
            return deny("ARTIFACT_DENIED", "Source artifact is unavailable to this principal/task.")
        artifact = dict(row)
        expected_kind = "data" if action.tool == "report.create" else "report"
        expected_resource = "sales_summary" if action.tool == "report.create" else "sales_report"
        if artifact["kind"] != expected_kind or artifact["resource"] != expected_resource:
            return deny("ARTIFACT_DENIED", "Artifact is not suitable for this operation.")
        if action.tool == "report.send":
            if args.recipient not in policy.destinations:
                return deny("DESTINATION_DENIED", "Destination is not allowlisted.")
            if artifact["sensitivity"] not in policy.export_sensitivities:
                return deny("EXPORT_DENIED", "Artifact sensitivity prohibits export.")
    # Measured anomaly: last ten recorded actions belonging to this principal.
    recent = c.execute("SELECT a.state FROM actions a JOIN governed_actions g USING(request_id) WHERE g.principal_id=? ORDER BY g.created_at DESC LIMIT 10", (principal.principal_id,)).fetchall()
    factors = {
        "impact": {"database.read": 0.0, "report.create": 0.25, "report.send": 0.75}[action.tool],
        "sensitivity": 0.25 if not artifact or artifact["sensitivity"] == "internal" else 1.0,
        "blast_radius": action.arguments.get("limit", 10) / 100 if action.tool == "database.read" else min(len(json.loads(artifact["data_json"]).get("rows", [])) / 100, 1),
        "external_egress": 1.0 if action.tool == "report.send" else 0.0,
        "provenance_uncertainty": 0.0,
        "recent_denials": sum(r[0] == "BLOCKED" for r in recent) / 10,
    }
    score = round(sum(policy.weights[k] * v for k, v in factors.items()), 2)
    category = "Low"
    for name in ("medium", "high", "critical"):
        if score >= policy.thresholds[name]:
            category = name.title()
    base["risk"] = {"score": score, "category": category, "factors": factors,
                    "explanation": "Weighted policy score; provenance is server tracked; recent_denials counts the last ten actions. Thresholds are initial policy choices, not probabilities."}
    base.update(decision="ALLOW", reason_code="AUTHORIZED", reason="Principal, task, capability and context checks passed.")
    if score >= policy.thresholds["critical"]:
        base.update(decision="BLOCK", reason_code="CRITICAL_RISK", reason="Risk exceeds critical policy threshold.")
    elif action.tool == "report.send" or score >= policy.thresholds["medium"]:
        base.update(decision="ESCALATE", reason_code="HUMAN_REVIEW_REQUIRED", reason="Human review required.")
    # Exclude volatile activity counters from binding, but re-evaluate their current score before execution.
    context = digest({"policy": policy.model_dump(), "artifact": artifact, "principal": principal.principal_id,
                      "role": principal.role, "task": action.task_id})
    return base, action, artifact, context

