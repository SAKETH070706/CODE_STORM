from governor.schemas import (
    ActionRequest,
    Decision,
    DecisionResponse,
)

from .database_tool import read_sales
from .report_tool import create_report
from .send_tool import send_report


class ExecutionDispatcher:

    """
    Restricted execution dispatcher.

    Only ALLOW decisions can reach this class.

    BLOCK and ESCALATE are rejected here as
    a second defense layer.
    """

    def execute(
        self,
        action: ActionRequest,
        decision: DecisionResponse,
    ) -> dict:

        # ==========================================
        # SECOND SECURITY BOUNDARY
        # ==========================================

        if decision.decision != Decision.ALLOW:

            raise PermissionError(
                "Execution denied: Governor decision "
                f"is {decision.decision.value}"
            )

        # ==========================================
        # DATABASE READ
        # ==========================================

        if action.tool == "database.read":

            if action.arguments.get(
                "action"
            ) != "read":

                raise PermissionError(
                    "database.read only supports read"
                )

            columns = action.arguments.get(
                "columns",
                [],
            )

            return {
                "tool": action.tool,
                "result": read_sales(
                    columns
                ),
            }

        # ==========================================
        # REPORT WRITE
        # ==========================================

        if action.tool == "report.write":

            if action.arguments.get(
                "action"
            ) != "create":

                raise PermissionError(
                    "report.write only supports create"
                )

            path = action.arguments.get(
                "path"
            )

            data = action.arguments.get(
                "data",
                [],
            )

            return {
                "tool": action.tool,
                "result": create_report(
                    path,
                    data,
                ),
            }

        # ==========================================
        # SEND REPORT
        # ==========================================

        if action.tool == "send.report":

            if action.arguments.get(
                "action"
            ) != "send":

                raise PermissionError(
                    "send.report only supports send"
                )

            destination = (
                action.arguments.get(
                    "destination"
                )
            )

            report_path = (
                action.arguments.get(
                    "report_path"
                )
            )

            return {
                "tool": action.tool,
                "result": send_report(
                    destination,
                    report_path,
                ),
            }

        raise PermissionError(
            f"No execution adapter for tool "
            f"'{action.tool}'"
        )