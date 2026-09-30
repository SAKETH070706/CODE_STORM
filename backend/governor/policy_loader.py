from pathlib import Path
from typing import Any

import yaml


BACKEND_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = BACKEND_DIR / "policies"


def _load(filename: str) -> dict[str, Any]:
    path = POLICY_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Policy file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid policy format: {filename}"
        )

    return data


def load_roles():
    return _load("roles.yaml")


def load_tasks():
    return _load("tasks.yaml")


def load_approval_rules():
    return _load("approval_rules.yaml")