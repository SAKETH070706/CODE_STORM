"""SQLAlchemy 2 persistence. PostgreSQL in deployment; SQLite only for isolated tests."""
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Integer, Text, JSON, ForeignKey, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return uuid4().hex


def utc():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    active_policy_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    audit_sequence: Mapped[int] = mapped_column(Integer, default=0)
    audit_head: Mapped[str] = mapped_column(String(64), default="0" * 64)
    created_at: Mapped[str] = mapped_column(String(40), default=utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)
    can_create_workspaces: Mapped[bool] = mapped_column(default=False)


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    groups: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)


class TenantRow:
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150), default="")
    state: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(40), default=utc)


class Source(TenantRow, Base):
    __tablename__ = "policy_sources"


class Policy(TenantRow, Base):
    __tablename__ = "policies"


class Agent(TenantRow, Base):
    __tablename__ = "agents"


class Task(TenantRow, Base):
    __tablename__ = "tasks"


class Connector(TenantRow, Base):
    __tablename__ = "connectors"


class ReviewerGroup(TenantRow, Base):
    __tablename__ = "reviewer_groups"


class Action(TenantRow, Base):
    __tablename__ = "workspace_actions"


class Artifact(TenantRow, Base):
    __tablename__ = "workspace_artifacts"


class Approval(TenantRow, Base):
    __tablename__ = "workspace_approvals"


class Outbox(TenantRow, Base):
    __tablename__ = "workspace_outbox"


class CompilationJob(TenantRow, Base):
    __tablename__ = "compilation_jobs"


class Credential(Base):
    __tablename__ = "agent_credentials"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    active: Mapped[bool] = mapped_column(default=True)


class Idempotency(Base):
    __tablename__ = "workspace_idempotency"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    principal_id: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(128))
    payload_digest: Mapped[str] = mapped_column(String(64))
    action_id: Mapped[str] = mapped_column(ForeignKey("workspace_actions.id"))
    __table_args__ = (UniqueConstraint("organization_id", "principal_id", "key"),)


class AuditEvent(Base):
    __tablename__ = "workspace_audit"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_json: Mapped[str] = mapped_column(Text)
    previous_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("organization_id", "sequence"),)


class LegacyStream(Base):
    __tablename__ = "legacy_streams"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    import_digest: Mapped[str] = mapped_column(String(64), unique=True)
    # Original event strings/hashes/sequence stored without recanonicalization.
    events: Mapped[list] = mapped_column(JSON)
    ownership_manifest: Mapped[dict] = mapped_column(JSON)


class Database:
    def __init__(self, url=None, testing=False):
        url = url or os.environ.get("DATABASE_URL", "")
        if not url.startswith("postgresql+psycopg://") and not (testing and url.startswith("sqlite")):
            raise RuntimeError("Set DATABASE_URL to postgresql+psycopg://; runtime SQLite is not supported")
        connect_args = {"connect_timeout": 10}
        if "-pooler" not in url:
            connect_args["options"] = "-c lock_timeout=3000 -c statement_timeout=10000"
        self.engine = create_engine(url, pool_pre_ping=True, **({"pool_timeout": 10, "connect_args": connect_args} if url.startswith("postgresql") else {}))
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self, organization_id=None):
        with self.sessions.begin() as s:
            if organization_id:
                org = s.scalar(select(Organization).where(Organization.id == organization_id).with_for_update())
                if org is None:
                    from fastapi import HTTPException
                    raise HTTPException(404, "Workspace not found")
            yield s


def owned(s, model, organization_id, record_id):
    from fastapi import HTTPException
    row = s.scalar(select(model).where(model.id == record_id, model.organization_id == organization_id))
    if row is None:
        raise HTTPException(404, "Record not found")
    return row


def listed(s, model, org, limit=200):
    return list(s.scalars(select(model).where(model.organization_id == org).order_by(model.created_at.desc()).limit(limit)))


def public(row):
    return {"id": row.id, "organization_id": row.organization_id, "name": row.name, "state": row.state, "data": row.data, "created_at": row.created_at}
