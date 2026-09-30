from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    action_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    task_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    tool: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    resource: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    arguments_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    decision: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    risk_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    execution_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    action_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("actions.action_id"),
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    result_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    event_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    action_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("actions.action_id"),
        index=True,
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    details_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    previous_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    event_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    approval_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    action_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("actions.action_id"),
        index=True,
        nullable=False,
    )

    action_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
    )

    requested_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    decided_by: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )