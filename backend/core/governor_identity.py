"""Demo identity boundary. Tokens are never stored in governance records."""
from __future__ import annotations
import os
import secrets
from typing import Optional
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


@dataclass(frozen=True)
class Principal:
    principal_id: str
    role: str
    permissions: frozenset[str] = frozenset()


def identities():
    entries = [
        (os.getenv("GOVERNOR_ANALYST_TOKEN", ""), Principal("analyst-1", "data_analyst")),
        (os.getenv("GOVERNOR_SUPPORT_TOKEN", ""), Principal("support-1", "customer_support")),
        (os.getenv("GOVERNOR_REVIEWER_TOKEN", ""), Principal(
            "reviewer-1", "reviewer", frozenset(filter(None, os.getenv(
                "GOVERNOR_REVIEWER_PERMISSIONS", "review,audit,knowledge_admin"
            ).split(","))))),
    ]
    tokens = [token for token, _ in entries]
    if any(len(t) < 32 or not t.isascii() or t.startswith("replace") for t in tokens) or len(set(tokens)) != len(tokens):
        raise RuntimeError("Configure three distinct ASCII governor tokens of at least 32 characters.")
    allowed = {"review", "audit", "knowledge_admin"}
    if not entries[-1][1].permissions <= allowed:
        raise RuntimeError("Unknown reviewer permission.")
    return entries


bearer = HTTPBearer(auto_error=False)


def get_principal(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    matched = None
    for token, principal in identities():
        if secrets.compare_digest(credentials.credentials.encode(), token.encode()):
            matched = principal
    if matched is None:
        raise HTTPException(401, "Invalid bearer token", headers={"WWW-Authenticate": "Bearer"})
    return matched


def require(principal, permission):
    if permission not in principal.permissions:
        raise HTTPException(403, "Permission denied")


def knowledge_admin(principal=Depends(get_principal)):
    require(principal, "knowledge_admin")
    return principal
