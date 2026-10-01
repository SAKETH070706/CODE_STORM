"""Workspace administration and transactional policy publication."""
import hashlib
import json
from pathlib import Path
from sqlalchemy import select
from fastapi import HTTPException
from workspace.models import (Organization, Membership, User, Source, Policy, Agent, Task, Connector, ReviewerGroup,
                              Credential, CompilationJob, Action, Artifact, Approval, Outbox, owned, listed, public, uid, utc)
from workspace.identity import require, PERMISSIONS, generate_key, PASSWORDS
from workspace.audit import append, digest
from workspace.rules import RuleSet, Rule, validate_rules, CAPABILITIES
from workspace.sources import isolated


class Administration:
    def __init__(self, db, storage):
        self.db, self.storage = db, storage

    def create_workspace(self, identity, name):
        with self.db.transaction() as s:
            user = s.get(User, identity.principal_id)
            if identity.kind != "human" or not user or not user.can_create_workspaces:
                raise HTTPException(403, "Workspace creation requires operator authorization")
            org = Organization(name=name); s.add(org); s.flush()
            s.add(Membership(organization_id=org.id, user_id=user.id, permissions=sorted(PERMISSIONS), groups=[]))
            append(s, org.id, user.id, "workspace.created", {"name": name})
            return {"id": org.id, "name": org.name}

    def members(self, identity):
        require(identity, "members")
        with self.db.transaction(identity.organization_id) as s:
            rows = list(s.execute(
                select(Membership, User.email)
                .join(User, Membership.user_id == User.id)
                .where(Membership.organization_id == identity.organization_id)
            ).all())
            return [{"id": m.id, "user_id": m.user_id, "email": email, "permissions": m.permissions, "groups": m.groups, "active": m.active} for m, email in rows]

    def add_member(self, identity, email, password, permissions, groups):
        require(identity, "members")
        if not set(permissions) <= PERMISSIONS:
            raise HTTPException(400, "Unknown workspace permission")
        with self.db.transaction(identity.organization_id) as s:
            for group in groups:
                owned(s, ReviewerGroup, identity.organization_id, group)
            user = s.scalar(select(User).where(User.email == email.lower()))
            if user is None:
                if password is None:
                    raise HTTPException(400, "New accounts need an initial password")
                user = User(email=email.lower(), password_hash=PASSWORDS.hash(password)); s.add(user); s.flush()
            elif password:
                raise HTTPException(409, "Cannot reset an existing account's password through membership management")
            member = s.scalar(select(Membership).where(Membership.organization_id == identity.organization_id, Membership.user_id == user.id))
            if member and member.user_id == identity.principal_id and "members" not in permissions:
                raise HTTPException(400, "Cannot remove your own member administration permission")
            if member is None:
                member = Membership(organization_id=identity.organization_id, user_id=user.id); s.add(member)
            member.permissions, member.groups, member.active = permissions, groups, True
            append(s, identity.organization_id, identity.principal_id, "membership.changed", {"user_id": user.id, "permissions": permissions, "groups": groups})
            return {"user_id": user.id}

    def registry(self, identity, model, data, name, record_id=None):
        permission = "connectors" if model is Connector else "members" if model is ReviewerGroup else "agents"
        require(identity, permission)
        with self.db.transaction(identity.organization_id) as s:
            if model is Connector:
                if data["kind"] not in CAPABILITIES:
                    raise HTTPException(400, "Unsupported connector")
                if any(not d.endswith("@example.test") or len(d) > 100 or any(c in d for c in '\r\n /') for d in data.get("destinations", [])):
                    raise HTTPException(400, "Simulated destinations must use example.test")
            if model is Task:
                import re
                if any(not re.fullmatch(r"[a-z][a-z0-9_-]{1,49}", role) for role in data["roles"]):
                    raise HTTPException(400, "Invalid business role identifier")
                for resource in data["resources"]:
                    owned(s, Connector, identity.organization_id, resource)
                for agent_id in data["agents"]:
                    agent = owned(s, Agent, identity.organization_id, agent_id)
                    if agent.data["role"] not in data["roles"]:
                        raise HTTPException(400, "Agent role is outside task roles")
            row = owned(s, model, identity.organization_id, record_id) if record_id else model(organization_id=identity.organization_id)
            row.name, row.data = name, data
            s.add(row); s.flush()
            append(s, identity.organization_id, identity.principal_id, model.__tablename__ + ".changed", {"record_id": row.id})
            return public(row)

    def key(self, identity, agent_id):
        require(identity, "agents")
        with self.db.transaction(identity.organization_id) as s:
            agent = owned(s, Agent, identity.organization_id, agent_id)
            if agent.state != "ACTIVE":
                raise HTTPException(409, "Agent is revoked")
            key, hashed = generate_key()
            credential = Credential(organization_id=identity.organization_id, agent_id=agent.id, key_hash=hashed)
            s.add(credential); s.flush()
            append(s, identity.organization_id, identity.principal_id, "credential.created", {"agent_id": agent.id, "credential_id": credential.id})
            return {"credential_id": credential.id, "key": key, "display": "once"}

    def revoke(self, identity, agent_id):
        require(identity, "agents")
        with self.db.transaction(identity.organization_id) as s:
            agent = owned(s, Agent, identity.organization_id, agent_id); agent.state = "REVOKED"
            for key in s.scalars(select(Credential).where(Credential.organization_id == identity.organization_id, Credential.agent_id == agent.id)):
                key.active = False
            append(s, identity.organization_id, identity.principal_id, "agent.revoked", {"agent_id": agent.id})
            return public(agent)

    def source(self, identity, filename, content=None, url=None, previous_id=None):
        require(identity, "sources")
        extension = Path(filename).suffix.lower()
        if not url and extension not in {".pdf", ".md", ".txt"}:
            raise HTTPException(400, "Upload PDF, Markdown or plain text")
        # Ownership checked before parsing, and again under the write lock.
        if previous_id:
            with self.db.transaction(identity.organization_id) as s:
                owned(s, Source, identity.organization_id, previous_id)
        try:
            raw, segments, extension = isolated(content, extension, url)
        except (ValueError, TimeoutError) as e:
            raise HTTPException(422, str(e)[:200])
        except Exception:
            raise HTTPException(422, "Source processing exceeded limits or is unavailable")
        key = self.storage.put(identity.organization_id, raw)
        with self.db.transaction(identity.organization_id) as s:
            previous = owned(s, Source, identity.organization_id, previous_id) if previous_id else None
            lineage = previous.data.get("lineage", previous.id) if previous else uid()
            revisions = [r.data["revision"] for r in listed(s, Source, identity.organization_id) if r.data.get("lineage") == lineage]
            source = Source(organization_id=identity.organization_id, name=Path(filename).name[:150], state="EXTRACTED", data={
                "storage_key": key, "content_hash": hashlib.sha256(raw).hexdigest(), "revision": max(revisions, default=0) + 1,
                "lineage": lineage, "uploader": identity.principal_id, "segments": segments, "extension": extension,
                "origin": "url" if url else "upload"})
            s.add(source); s.flush()
            draft = Policy(organization_id=identity.organization_id, name="Review " + source.name, state="DRAFT", data={"rules": [], "revision": 1, "sources": [source.id], "validation_errors": ["Add and review structured rules"], "digest": None})
            s.add(draft); s.flush()
            append(s, identity.organization_id, identity.principal_id, "source.revised" if previous else "source.uploaded", {"source_id": source.id, "revision": source.data["revision"], "content_hash": source.data["content_hash"], "draft_id": draft.id})
            result = public(source); result["draft_id"] = draft.id
            result["data"] = {k: v for k, v in source.data.items() if k != "storage_key"}
            return result

    def draft(self, identity, rules, name, policy_id=None, expected_revision=None):
        require(identity, "drafts")
        parsed = RuleSet.model_validate({"rules": rules})
        with self.db.transaction(identity.organization_id) as s:
            policy = owned(s, Policy, identity.organization_id, policy_id) if policy_id else Policy(organization_id=identity.organization_id, state="DRAFT", data={"revision": 0})
            if policy.state not in {"DRAFT", "VALIDATED"}:
                raise HTTPException(409, "Published versions cannot be edited; clone to a new draft")
            if policy_id and expected_revision != policy.data["revision"]:
                raise HTTPException(409, "Draft changed; reload before editing")
            for rule in parsed.rules:
                owned(s, Source, identity.organization_id, rule.source.source_id)
            policy.state, policy.name = "DRAFT", name
            policy.data = {"rules": [r.model_dump() for r in parsed.rules], "revision": policy.data["revision"] + 1, "validation_errors": [], "digest": None}
            s.add(policy); s.flush()
            append(s, identity.organization_id, identity.principal_id, "policy.edited", {"policy_id": policy.id, "revision": policy.data["revision"]})
            return public(policy)

    def validation(self, s, org, policy):
        rules = RuleSet.model_validate({"rules": policy.data["rules"]}).rules
        sources = {r.id: r.data for r in listed(s, Source, org)}
        connectors = {r.id: r.data for r in listed(s, Connector, org) if r.state == "ACTIVE"}
        tasks = {r.id: r.data for r in listed(s, Task, org) if r.state == "ACTIVE"}
        groups = {r.id for r in listed(s, ReviewerGroup, org) if r.state == "ACTIVE"}
        return validate_rules(rules, sources, connectors, tasks, groups) or ([] if rules else ["Empty policies cannot publish; use explicit BLOCK rules"])

    def validate(self, identity, policy_id):
        require(identity, "drafts")
        with self.db.transaction(identity.organization_id) as s:
            policy = owned(s, Policy, identity.organization_id, policy_id)
            if policy.state not in {"DRAFT", "VALIDATED"}:
                raise HTTPException(409, "Only drafts can be validated")
            errors = self.validation(s, identity.organization_id, policy)
            policy.data = {**policy.data, "validation_errors": errors}
            policy.state = "DRAFT" if errors else "VALIDATED"
            append(s, identity.organization_id, identity.principal_id, "policy.validated", {"policy_id": policy.id, "valid": not errors})
            return public(policy)

    def publish(self, identity, policy_id, expected_active):
        require(identity, "publish")
        with self.db.transaction(identity.organization_id) as s:
            org = s.get(Organization, identity.organization_id)
            if org.active_policy_id != expected_active:
                raise HTTPException(409, "Active policy changed; inspect the new diff before publishing")
            policy = owned(s, Policy, org.id, policy_id)
            if policy.state != "VALIDATED" or self.validation(s, org.id, policy):
                raise HTTPException(409, "Draft must pass current validation before publishing")
            if org.active_policy_id:
                owned(s, Policy, org.id, org.active_policy_id).state = "SUPERSEDED"
            policy.state = "PUBLISHED"
            policy.data = {**policy.data, "digest": digest(policy.data["rules"]), "published_at": utc(), "publisher": identity.principal_id}
            org.active_policy_id = policy.id
            append(s, org.id, identity.principal_id, "policy.published", {"policy_id": policy.id, "policy_digest": policy.data["digest"]})
            return public(policy)

    def clone(self, identity, policy_id):
        require(identity, "drafts")
        with self.db.transaction(identity.organization_id) as s:
            source = owned(s, Policy, identity.organization_id, policy_id)
            clone = Policy(organization_id=identity.organization_id, name=source.name + " (new version)", state="DRAFT", data={"rules": source.data["rules"], "revision": 1, "validation_errors": [], "cloned_from": source.id})
            s.add(clone); s.flush()
            append(s, identity.organization_id, identity.principal_id, "policy.cloned", {"policy_id": clone.id, "from_id": source.id})
            return public(clone)
