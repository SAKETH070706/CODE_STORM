from governor.pipeline import GovernorPipeline
from governor.schemas import (
    ActionRequest,
    Decision,
    TrustedActionContext,
)


def context():

    return TrustedActionContext(
        agent_id="demo-data-analyst",
        role="data_analyst",
        task_scope="sales-report",
        provenance="trusted_internal",
        environment="local",
    )


def test_allowed_database_read():

    pipeline = GovernorPipeline()

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

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.ALLOW
    assert result.state.value == "ALLOWED"
    assert result.requires_approval is False


def test_report_creation_allowed():

    pipeline = GovernorPipeline()

    action = ActionRequest(
        task_id="sales-report",
        tool="report.write",
        resource="reports",
        arguments={
            "action": "create",
            "path": "data/reports/report.txt",
        },
    )

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.ALLOW


def test_external_send_escalates():

    pipeline = GovernorPipeline()

    action = ActionRequest(
        task_id="sales-report",
        tool="send.report",
        resource="approved_external_destination",
        arguments={
            "action": "send",
            "destination": "manager@example.com",
        },
    )

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.ESCALATE
    assert result.requires_approval is True
    assert (
        result.state.value
        == "PENDING_APPROVAL"
    )


def test_delete_is_blocked():

    pipeline = GovernorPipeline()

    action = ActionRequest(
        task_id="sales-report",
        tool="database.read",
        resource="sales_summary",
        arguments={
            "action": "delete",
        },
    )

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.BLOCK


def test_unknown_tool_is_blocked():

    pipeline = GovernorPipeline()

    action = ActionRequest(
        task_id="sales-report",
        tool="shell.execute",
        resource="server",
        arguments={
            "action": "execute",
            "command": "dir",
        },
    )

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.BLOCK


def test_sensitive_resource_is_blocked():

    pipeline = GovernorPipeline()

    action = ActionRequest(
        task_id="sales-report",
        tool="database.read",
        resource="credentials",
        arguments={
            "action": "read",
            "columns": ["month"],
        },
    )

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.BLOCK


def test_invalid_column_is_blocked():

    pipeline = GovernorPipeline()

    action = ActionRequest(
        task_id="sales-report",
        tool="database.read",
        resource="sales_summary",
        arguments={
            "action": "read",
            "columns": [
                "month",
                "DROP TABLE sales",
            ],
        },
    )

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.BLOCK


def test_path_traversal_is_blocked():

    pipeline = GovernorPipeline()

    action = ActionRequest(
        task_id="sales-report",
        tool="report.write",
        resource="reports",
        arguments={
            "action": "create",
            "path": "../../secret.txt",
        },
    )

    result = pipeline.evaluate(
        action,
        context(),
    )

    assert result.decision == Decision.BLOCK