from __future__ import annotations

from .schemas import (
    AgentActionProposal,
    AgentTaskRequest,
)


class AgentPlanner:
    """
    Case 7 deterministic agent planner.

    The planner converts a task into an action proposal.

    IMPORTANT:
    The planner does NOT execute anything.

    It only proposes an action.
    """

    def plan(
        self,
        task: AgentTaskRequest,
    ) -> AgentActionProposal:

        return AgentActionProposal(
            task_id=task.task_id,
            tool=task.tool,
            resource=task.resource,
            arguments=task.arguments,
        )
    