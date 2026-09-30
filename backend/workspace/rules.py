"""Bounded policy language; documents and model confidence are never authority."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

class Citation(Strict):
    source_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    revision: int = Field(ge=1)
    segment: int = Field(ge=1, le=1000)
    passage: str = Field(min_length=1, max_length=1500)

class Constraints(Strict):
    max_rows: int = Field(default=100, ge=1, le=100)
    formats: list[Literal["csv", "json"]] = Field(default_factory=lambda: ["csv", "json"], min_length=1, max_length=2)
    destinations: list[str] = Field(default_factory=list, max_length=20)

class Rule(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    role: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,49}$")
    tool: Literal["database.read", "report.create", "report.send"]
    resource: str = Field(pattern=r"^[a-f0-9]{32}$")
    tasks: list[str] = Field(min_length=1, max_length=30)
    arguments: Constraints = Field(default_factory=Constraints)
    decision: Literal["ALLOW", "ESCALATE", "BLOCK"]
    reviewer_group: str | None = Field(default=None, max_length=32)
    source: Citation
    assumptions: list[str] = Field(default_factory=list, max_length=10)
    ambiguity: list[str] = Field(default_factory=list, max_length=10)

class RuleSet(Strict):
    rules: list[Rule] = Field(max_length=100)

# No wildcard, expression, arbitrary SQL, path or network connector exists.
CAPABILITIES = {
    "demo_sales": {"database.read"}, "demo_support": {"database.read"},
    "report_storage": {"report.create"}, "simulated_delivery": {"report.send"},
}


def validate_rules(rules, sources, connectors, tasks, groups):
    errors = []
    seen = set()
    for rule in rules:
        prefix = rule.id + ": "
        if rule.id in seen:
            errors.append(prefix + "duplicate rule ID")
        seen.add(rule.id)
        if rule.assumptions or rule.ambiguity:
            errors.append(prefix + "resolve assumptions and ambiguity before publishing")
        source = sources.get(rule.source.source_id)
        if not source or source.get("revision") != rule.source.revision:
            errors.append(prefix + "source revision is missing")
        else:
            segments = source.get("segments", [])
            segment = next((s for s in segments if s["index"] == rule.source.segment), None)
            if not segment or rule.source.passage not in segment["text"]:
                errors.append(prefix + "supporting passage does not match the source segment")
        connector = connectors.get(rule.resource)
        if not connector or rule.tool not in CAPABILITIES.get(connector.get("kind"), set()):
            errors.append(prefix + "resource cannot implement this tool")
        for task in rule.tasks:
            if task not in tasks or rule.role not in tasks[task].get("roles", []):
                errors.append(prefix + "task or task role is unavailable")
        if rule.decision == "ESCALATE" and rule.reviewer_group not in groups:
            errors.append(prefix + "choose an existing reviewer group")
        if rule.tool == "report.send":
            destinations = rule.arguments.destinations
            allowed = connector.get("destinations", []) if connector else []
            if not destinations or any(d not in allowed for d in destinations):
                errors.append(prefix + "destinations must be explicit and supported by the connector")
        elif rule.arguments.destinations:
            errors.append(prefix + "destination constraints only apply to report.send")
    for i, left in enumerate(rules):
        for right in rules[i + 1:]:
            overlap = (left.role == right.role and left.tool == right.tool and left.resource == right.resource and bool(set(left.tasks) & set(right.tasks)))
            if overlap and left.decision == right.decision == "ESCALATE" and left.reviewer_group != right.reviewer_group:
                errors.append(f"{left.id}/{right.id}: overlapping escalation rules require different reviewer groups")
            if overlap and left.decision == right.decision and left.arguments == right.arguments and left.source == right.source:
                errors.append(f"{left.id}/{right.id}: redundant overlapping rules; remove the duplicate")
    return errors


def matching(rules, role, action):
    matches = []
    for r in rules:
        if r.role != role or r.tool != action["tool"] or r.resource != action["resource"] or action["task_id"] not in r.tasks:
            continue
        args = action["arguments"]
        if r.tool == "database.read" and args.get("limit", 10) > r.arguments.max_rows:
            continue
        if r.tool == "report.create" and args.get("format", "csv") not in r.arguments.formats:
            continue
        if r.tool == "report.send" and args.get("recipient") not in r.arguments.destinations:
            continue
        matches.append(r)
    if not matches:
        return "BLOCK", []
    decision = max((r.decision for r in matches), key={"ALLOW": 0, "ESCALATE": 1, "BLOCK": 2}.get)
    return decision, matches
