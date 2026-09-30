class RiskEngine:

    ACTION_SCORES = {
        "read": 5,
        "create": 20,
        "send": 25,
        "update": 40,
        "delete": 70,
        "truncate": 80,
        "drop": 90,
    }

    SENSITIVE_RESOURCES = {
        "customer_data",
        "financial_data",
        "credentials",
        "secrets",
        "api_keys",
    }

    def assess(
        self,
        tool: str,
        action: str,
        resource: str,
        provenance: str,
        environment: str,
        arguments: dict,
    ):

        score = self.ACTION_SCORES.get(
            action,
            50,
        )

        factors = []

        if action == "create":
            factors.append("state_creation")

        elif action == "update":
            factors.append("state_mutation")

        elif action in {
            "delete",
            "truncate",
            "drop",
        }:
            factors.append("destructive_action")

        elif action == "send":
            factors.append("external_transfer")

        if resource in self.SENSITIVE_RESOURCES:

            score += 25

            factors.append(
                "sensitive_data"
            )

        if provenance in {
            "untrusted_external",
            "web_scrape_unverified",
        }:

            score += 25

            factors.append(
                "untrusted_provenance"
            )

        if environment == "production":

            score += 20

            factors.append(
                "production_environment"
            )

        if tool == "send.report":

            score += 10

            factors.append(
                "external_report_destination"
            )

        score = min(score, 100)

        if score >= 80:
            level = "CRITICAL"

        elif score >= 60:
            level = "HIGH"

        elif score >= 30:
            level = "MEDIUM"

        else:
            level = "LOW"

        return score, level, factors