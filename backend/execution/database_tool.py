from pathlib import Path
import csv


BACKEND_DIR = Path(__file__).resolve().parent.parent

SALES_FILE = (
    BACKEND_DIR
    / "data"
    / "source_data"
    / "sales.csv"
)


ALLOWED_COLUMNS = {
    "month",
    "region",
    "product",
    "total_sales",
}


def read_sales(
    columns: list[str],
) -> list[dict]:

    """
    Restricted database operation.

    IMPORTANT:
    This is NOT arbitrary SQL execution.

    The agent can only request approved
    columns from the synthetic sales dataset.
    """

    if not columns:
        raise ValueError(
            "At least one column is required"
        )

    invalid_columns = [
        column
        for column in columns
        if column not in ALLOWED_COLUMNS
    ]

    if invalid_columns:
        raise PermissionError(
            "Unauthorized database column(s): "
            + ", ".join(invalid_columns)
        )

    if not SALES_FILE.exists():
        raise FileNotFoundError(
            f"Sales dataset not found: {SALES_FILE}"
        )

    results = []

    with SALES_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            results.append(
                {
                    column: row[column]
                    for column in columns
                }
            )

    return results