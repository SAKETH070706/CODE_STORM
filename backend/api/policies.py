from pathlib import Path

from fastapi import APIRouter

import yaml


# ===================================================================
# ROUTER
# ===================================================================

router = APIRouter(
    prefix="/api",
    tags=["Policies"],
)


# ===================================================================
# POLICY DIRECTORY
# ===================================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

POLICY_DIR = (
    BASE_DIR / "policies"
)


# ===================================================================
# YAML LOADER
# ===================================================================


def load_policy(
    filename: str,
):

    path = (
        POLICY_DIR / filename
    )

    if not path.exists():

        return {
            "error":
                f"{filename} not found"
        }

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return (
            yaml.safe_load(file)
            or {}
        )


# ===================================================================
# GET /api/policies
# ===================================================================


@router.get(
    "/policies"
)
def get_policies():

    return {

        "role_policies":
            load_policy(
                "roles.yaml"
            ),

        "task_policies":
            load_policy(
                "tasks.yaml"
            ),

        "approval_rules":
            load_policy(
                "approval_rules.yaml"
            ),
    }