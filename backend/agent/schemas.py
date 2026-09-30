from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class AgentTaskRequest(BaseModel):
    """
    User-level task submitted to the agent.
    """

    task_id: str

    instruction: str

    tool: str

    resource: str

    arguments: Dict[str, Any] = Field(
        default_factory=dict
    )


class AgentActionProposal(BaseModel):
    """
    Action proposed by the agent.

    This is NOT trusted execution authority.

    The proposal must still pass through
    the Agent Permission Governor.
    """

    task_id: str

    tool: str

    resource: str

    arguments: Dict[str, Any] = Field(
        default_factory=dict
    )


class AgentWorkflowResponse(BaseModel):
    """
    Result returned by the agent workflow.
    """

    task_id: str

    action_id: str

    decision: str

    state: str

    reason: str

    risk: Dict[str, Any]

    requires_approval: bool

    approval_id: str | None = None

    execution: Dict[str, Any] | None = None

    latency_ms: float