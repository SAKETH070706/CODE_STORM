from datetime import datetime, timezone


APPROVED_DESTINATIONS = {
    "manager@example.com",
}


def send_report(
    destination: str,
    report_path: str,
) -> dict:

    """
    Local mock of external report delivery.

    No real external network request is made
    during the local MVP.
    """

    if destination not in APPROVED_DESTINATIONS:

        raise PermissionError(
            "Destination is not approved"
        )

    return {
        "status": "mock_sent",
        "destination": destination,
        "report_path": report_path,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }