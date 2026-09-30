from pathlib import Path
import json


BACKEND_DIR = Path(__file__).resolve().parent.parent

REPORT_ROOT = (
    BACKEND_DIR
    / "data"
    / "reports"
).resolve()


def _safe_report_path(
    path: str,
) -> Path:

    if not path:
        raise ValueError(
            "Report path is required"
        )

    requested = Path(path)

    if not requested.is_absolute():
        requested = BACKEND_DIR / requested

    target = requested.resolve()

    try:
        target.relative_to(REPORT_ROOT)

    except ValueError:

        raise PermissionError(
            "Report path is outside "
            "the approved report directory"
        )

    return target


def create_report(
    path: str,
    data: list[dict],
) -> dict:

    """
    Create a report only inside
    backend/data/reports.
    """

    target = _safe_report_path(path)

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "report_type": "sales_report",
        "rows": data,
    }

    target.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "status": "created",
        "path": str(target),
        "rows": len(data),
    }