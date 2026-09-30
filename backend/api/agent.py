from fastapi import APIRouter, HTTPException

from agent.schemas import (
    AgentTaskRequest,
    AgentWorkflowResponse,
)

from agent.workflow import AgentWorkflow


router = APIRouter(
    prefix="/api/agent",
    tags=["Agent"],
)


workflow = AgentWorkflow()


@router.post(
    "/run",
    response_model=AgentWorkflowResponse,
)
def run_agent(
    task: AgentTaskRequest,
):

    try:

        result = workflow.run(
            task
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Agent workflow failed: "
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )