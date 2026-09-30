from agent.planner import AgentPlanner
from agent.schemas import AgentTaskRequest


def test_agent_planner_creates_action():

    task = AgentTaskRequest(
        task_id="sales-report",
        instruction="Read monthly sales",
        tool="database.read",
        resource="sales_summary",
        arguments={
            "action": "read",
            "columns": [
                "month",
                "total_sales",
            ],
        },
    )

    planner = AgentPlanner()

    proposal = planner.plan(task)

    assert proposal.task_id == "sales-report"

    assert proposal.tool == "database.read"

    assert proposal.resource == "sales_summary"

    assert proposal.arguments["action"] == "read"


def test_agent_planner_does_not_execute():

    task = AgentTaskRequest(
        task_id="sales-report",
        instruction="Read monthly sales",
        tool="database.read",
        resource="sales_summary",
        arguments={
            "action": "read",
        },
    )

    planner = AgentPlanner()

    proposal = planner.plan(task)

    # Planner only proposes.
    # It must not contain an execution result.

    assert not hasattr(
        proposal,
        "execution",
    )