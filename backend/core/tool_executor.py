import sqlite3
from contextlib import closing
from typing import Any

from core.demo_data import DEMO_DB_PATH
from core.permission_governor import (
    ActionRequest,
    AuthorizationResponse,
    ReadArguments,
)


# These queries are controlled by the server.
# The agent cannot supply SQL or choose a database file.
READ_QUERIES = {
    "sales_summary": """
        SELECT month, total_sales
        FROM sales_summary
        ORDER BY
            CASE month
                WHEN 'January' THEN 1
                WHEN 'February' THEN 2
                WHEN 'March' THEN 3
                ELSE 4
            END
        LIMIT ?
    """,
    "support_summary": """
        SELECT status, tickets
        FROM support_summary
        ORDER BY status
        LIMIT ?
    """,
}


def execute_authorized_read(*args, **kwargs):
    """Compatibility name only: evaluation responses are not execution permits."""
    raise PermissionError("Use Governor.submit; a durable execution claim is required")
