from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

ALLOWED_REPORT_ROOT = (
    BACKEND_DIR / "data" / "reports"
).resolve()


ALLOWED_DATABASE_COLUMNS = {
    "month",
    "region",
    "product",
    "total_sales",
}


def validate_report_path(
    path: str,
) -> tuple[bool, str]:

    if not path:
        return False, "Report path is required"

    target = Path(path)

    if not target.is_absolute():
        target = BACKEND_DIR / target

    target = target.resolve()

    try:
        target.relative_to(
            ALLOWED_REPORT_ROOT
        )

    except ValueError:

        return (
            False,
            "Path is outside approved "
            "report directory",
        )

    return True, "Valid report path"


def validate_database_columns(
    columns: list[str],
) -> tuple[bool, str]:

    if not isinstance(columns, list):
        return False, "Columns must be a list"

    if not columns:
        return False, "No columns supplied"

    invalid = [
        column
        for column in columns
        if column not in ALLOWED_DATABASE_COLUMNS
    ]

    if invalid:
        return (
            False,
            f"Unauthorized column(s): "
            f"{', '.join(invalid)}",
        )

    return True, "Valid database columns"


def validate_action_arguments(
    tool: str,
    action: str,
    arguments: dict,
) -> tuple[bool, str]:

    if tool == "database.read":

        if action != "read":
            return (
                False,
                "database.read only supports read",
            )

        return validate_database_columns(
            arguments.get("columns", [])
        )

    if tool == "report.write":

        if action != "create":
            return (
                False,
                "report.write only supports create",
            )

        return validate_report_path(
            arguments.get("path", "")
        )

    if tool == "send.report":

        if action != "send":
            return (
                False,
                "send.report only supports send",
            )

        destination = arguments.get(
            "destination"
        )

        if not destination:
            return (
                False,
                "Destination is required",
            )

        return True, "Valid destination"

    return (
        False,
        f"No validator exists for tool '{tool}'",
    )