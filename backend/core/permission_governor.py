from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


# The server owns these permissions.
# An agent cannot assign itself a role through its request.
ROLE_PERMISSIONS = {
    "data_analyst": {
        "database.read": {"sales_summary"},
        "report.create": {"sales_report"},
        "report.send": {"sales_report"},
    },
    "customer_support": {
        "database.read": {"support_summary"},
    },
}


# Server-defined task boundaries.
TASK_POLICIES = {
    "sales-report": {
        "roles": {"data_analyst"},
        "tools": {
            "database.read",
            "report.create",
            "report.send",
        },
        "resources": {
            "sales_summary",
            "sales_report",
        },
    },
    "support-review": {
        "roles": {"customer_support"},
        "tools": {"database.read"},
        "resources": {"support_summary"},
    },
}


class ActionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    task_id: str = Field(min_length=1, max_length=80)
    tool: str = Field(min_length=1, max_length=80)
    resource: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ReadArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    limit: int = Field(default=10, ge=1, le=100)


class CreateReportArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    report_id: Literal["monthly-sales"]
    format: Literal["csv", "json"] = "csv"


class SendReportArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    report_id: Literal["monthly-sales"]

    # A controlled example recipient.
    # No actual email will be sent in this stage.
    recipient: Literal["review@example.test"]


class AuthorizationResponse(BaseModel):
    decision: Literal["ALLOW", "BLOCK", "ESCALATE"]
    reason_code: str
    reason: str
    role: str
    policy_version: str = "png5-stage1-v1"

    # Authorization only. No executor exists in this step.
    executed: bool = False


ARGUMENT_SCHEMAS = {
    "database.read": ReadArguments,
    "report.create": CreateReportArguments,
    "report.send": SendReportArguments,
}


def authorize_action(
    action: ActionRequest,
    role: str,
) -> AuthorizationResponse:

    def respond(decision: str, code: str, reason: str):
        return AuthorizationResponse(
            decision=decision,
            reason_code=code,
            reason=reason,
            role=role,
        )

    # 1. Verify the server-assigned role.
    permissions = ROLE_PERMISSIONS.get(role)

    if permissions is None:
        return respond(
            "BLOCK",
            "UNKNOWN_ROLE",
            "The authenticated role is not recognized.",
        )

    # 2. Unknown tools are denied by default.
    if action.tool not in ARGUMENT_SCHEMAS:
        return respond(
            "BLOCK",
            "TOOL_NOT_SUPPORTED",
            "This tool is not enabled by the governor.",
        )

    # 3. Verify role permission for the tool and resource.
    permitted_resources = permissions.get(action.tool, set())

    if action.resource not in permitted_resources:
        return respond(
            "BLOCK",
            "ROLE_RESOURCE_DENIED",
            "Your role cannot use this tool on this resource.",
        )

    # 4. Verify the task assignment.
    task = TASK_POLICIES.get(action.task_id)

    if task is None or role not in task["roles"]:
        return respond(
            "BLOCK",
            "TASK_DENIED",
            "This task is not assigned to your role.",
        )

    # 5. Verify the action remains inside task boundaries.
    if (
        action.tool not in task["tools"]
        or action.resource not in task["resources"]
    ):
        return respond(
            "BLOCK",
            "TASK_SCOPE_DENIED",
            "The action exceeds the authorized task scope.",
        )

    # 6. Validate tool-specific arguments.
    schema = ARGUMENT_SCHEMAS[action.tool]

    try:
        schema.model_validate(action.arguments)
    except ValidationError:
        return respond(
            "BLOCK",
            "INVALID_ARGUMENTS",
            "The tool arguments are invalid or contain unsupported fields.",
        )

    # 7. External sends require review.
    if action.tool == "report.send":
        return respond(
            "ESCALATE",
            "HUMAN_REVIEW_REQUIRED",
            "Human approval is required. Nothing has executed.",
        )

    return respond(
        "ALLOW",
        "AUTHORIZED",
        "The action satisfies role, task, resource and argument policies.",
    )