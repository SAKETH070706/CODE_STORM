import pytest

from execution.database_tool import read_sales
from execution.report_tool import create_report
from execution.send_tool import send_report
from execution.dispatcher import ExecutionDispatcher

from governor.pipeline import GovernorPipeline
from governor.schemas import (
    ActionRequest,
    Decision,
    TrustedActionContext,
)


def make_context():

    return TrustedActionContext(
        agent_id="demo-data-analyst",
        role="data_analyst",
        task_scope="sales-report",
        provenance="trusted_internal",
        environment="local",
    )


def test_database_tool_reads_allowed_columns():

    result = read_sales(
        ["month", "total_sales"]
    )

    assert len(result) > 0

    assert "month" in result[0]
    assert "total_sales" in result[0]


def test_database_tool_rejects_unauthorized_column():

    with pytest.raises(PermissionError):

        read_sales(
            [
                "month",
                "password",
            ]
        )


def test_report_tool_creates_inside_allowed_directory(
    tmp_path,
):

    # We don't use tmp_path as the report root.
    # The execution tool must remain inside
    # backend/data/reports.

    result = create_report(
        "data/reports/test_case3_report.json",
        [
            {
                "month": "January",
                "total_sales": "125000",
            }
        ],
    )

    assert result["status"] == "created"


def test_report_tool_rejects_path_traversal():

    with pytest.raises(PermissionError):

        create_report(
            "../../secret.json",
            [],
        )


def test_send_tool_rejects_unapproved_destination():

    with pytest.raises(PermissionError):

        send_report(
            "attacker@example.com",
            "report.json",
        )


def test_dispatcher_allows_governor_allowed_action():

    governor = GovernorPipeline()
    dispatcher = ExecutionDispatcher()

    action = ActionRequest(
        task_id="sales-report",
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

    decision = governor.evaluate(
        action,
        make_context(),
    )

    assert decision.decision == Decision.ALLOW

    result = dispatcher.execute(
        action,
        decision,
    )

    assert result["tool"] == "database.read"
    assert len(result["result"]) > 0


def test_dispatcher_rejects_block():

    governor = GovernorPipeline()
    dispatcher = ExecutionDispatcher()

    action = ActionRequest(
        task_id="sales-report",
        tool="database.read",
        resource="sales_summary",
        arguments={
            "action": "delete",
        },
    )

    decision = governor.evaluate(
        action,
        make_context(),
    )

    assert decision.decision == Decision.BLOCK

    with pytest.raises(PermissionError):

        dispatcher.execute(
            action,
            decision,
        )


def test_dispatcher_rejects_escalation():

    governor = GovernorPipeline()
    dispatcher = ExecutionDispatcher()

    action = ActionRequest(
        task_id="sales-report",
        tool="send.report",
        resource="approved_external_destination",
        arguments={
            "action": "send",
            "destination": "manager@example.com",
        },
    )

    decision = governor.evaluate(
        action,
        make_context(),
    )

    assert decision.decision == Decision.ESCALATE

    with pytest.raises(PermissionError):

        dispatcher.execute(
            action,
            decision,
        )


def test_unknown_tool_cannot_execute():

    dispatcher = ExecutionDispatcher()

    action = ActionRequest(
        task_id="sales-report",
        tool="shell.execute",
        resource="server",
        arguments={
            "action": "execute",
        },
    )

    # We intentionally construct an ALLOW-shaped
    # decision to verify the dispatcher still
    # refuses unknown tools.

    from governor.schemas import (
        DecisionResponse,
        ActionState,
        RiskAssessment,
    )

    fake_decision = DecisionResponse(
        action_id="test",
        decision=Decision.ALLOW,
        state=ActionState.ALLOWED,
        reason="test",
        risk=RiskAssessment(
            score=0,
            level="LOW",
            factors=[],
        ),
        requires_approval=False,
        latency_ms=0,
    )

    with pytest.raises(PermissionError):

        dispatcher.execute(
            action,
            fake_decision,
        )