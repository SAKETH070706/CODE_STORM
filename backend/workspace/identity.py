"""Local account and agent authentication; no public privileged signup."""
import hashlib
import os
import secrets
import time
from dataclasses import dataclass
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException
from sqlalchemy import select
from workspace.models import User, Membership, Credential, Agent, owned

PERMISSIONS = frozenset({"members", "sources", "drafts", "publish", "agents", "connectors", "review", "audit", "activity", "playground"})
PASSWORDS = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

@dataclass(frozen=True)
class Identity:
    principal_id: str
    organization_id: str
    kind: str
    role: str = ""
    permissions: frozenset = frozenset()
    groups: frozenset = frozenset()
    credential_id: str | None = None
    legacy_demo: bool = False
    auth_time: int = 0  # original sign-in time (epoch s); preserved across refreshes


def signing_secret():
    value = os.environ.get("WORKSPACE_SIGNING_SECRET", "")
    if len(value) < 48 or value.startswith("replace"):
        raise RuntimeError("Set a random WORKSPACE_SIGNING_SECRET of at least 48 characters")
    return value


def require(identity, permission):
    if identity.kind != "human" or permission not in identity.permissions:
        raise HTTPException(403, "Workspace permission denied")


TOKEN_SECONDS = 900
MAX_SESSION_SECONDS = 8 * 3600  # absolute cap: refreshing never extends a sign-in beyond this


def token_for(user_id, org, auth_time=None):
    now = int(time.time())
    auth = int(auth_time) if auth_time else now
    # A refreshed token can never outlive the original sign-in by more than the absolute cap.
    exp = min(now + TOKEN_SECONDS, auth + MAX_SESSION_SECONDS)
    return jwt.encode({"sub": user_id, "org": org, "iat": now, "auth": auth, "exp": exp,
                       "iss": "png5-local", "aud": "png5-workspace"}, signing_secret(), algorithm="HS256")


def resolve(s, token):
    demo_mode = os.getenv("WORKSPACE_DEMO_MODE", "false").lower() == "true"
    reviewer_token = os.getenv("GOVERNOR_REVIEWER_TOKEN", "")
    if demo_mode and len(reviewer_token) >= 32 and secrets.compare_digest(token.encode(), reviewer_token.encode()):
        org = os.getenv("DEMO_ORGANIZATION_ID", "")
        user_id = os.getenv("DEMO_REVIEWER_USER_ID", "")
        user = s.get(User, user_id)
        member = s.scalar(select(Membership).where(Membership.organization_id == org, Membership.user_id == user_id, Membership.active.is_(True)))
        if not user or not user.active or not member:
            raise HTTPException(401, "Imported demo reviewer mapping is unavailable")
        return Identity(user.id, org, "human", permissions=frozenset(member.permissions) & frozenset({"review", "audit", "activity"}), groups=frozenset(member.groups), legacy_demo=True)
    if token.startswith("agent_") or (demo_mode and token.count(".") != 2):
        hashed = hashlib.sha256(token.encode()).hexdigest()
        credential = s.scalar(select(Credential).where(Credential.key_hash == hashed, Credential.active.is_(True)))
        if credential is None:
            raise HTTPException(401, "Invalid or revoked credential")
        agent = owned(s, Agent, credential.organization_id, credential.agent_id)
        if agent.state != "ACTIVE":
            raise HTTPException(401, "Agent is revoked")
        return Identity(agent.id, agent.organization_id, "agent", agent.data["role"], credential_id=credential.id, legacy_demo=not token.startswith("agent_"))
    try:
        claims = jwt.decode(token, signing_secret(), algorithms=["HS256"], audience="png5-workspace", issuer="png5-local",
                            options={"require": ["exp", "iat", "sub", "org"]})
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired or invalid")
    auth_time = int(claims.get("auth", claims["iat"]))
    if time.time() - auth_time > MAX_SESSION_SECONDS:
        raise HTTPException(401, "Session expired; sign in again")
    user = s.get(User, claims["sub"])
    member = s.scalar(select(Membership).where(Membership.user_id == claims["sub"], Membership.organization_id == claims["org"], Membership.active.is_(True)))
    if not user or not user.active or not member:
        raise HTTPException(401, "Membership no longer active")
    return Identity(user.id, member.organization_id, "human", permissions=frozenset(member.permissions), groups=frozenset(member.groups), auth_time=auth_time)


def login(s, email, password):
    user = s.scalar(select(User).where(User.email == email.lower().strip(), User.active.is_(True)))
    # Same expensive path when the account does not exist; no account enumeration response.
    encoded = user.password_hash if user else PASSWORDS.hash(secrets.token_urlsafe(24))
    try:
        PASSWORDS.verify(encoded, password)
    except VerificationError:
        raise HTTPException(401, "Invalid account credentials")
    if user is None:
        raise HTTPException(401, "Invalid account credentials")
    memberships = list(s.scalars(select(Membership).where(Membership.user_id == user.id, Membership.active.is_(True))))
    return user, memberships


def generate_key():
    key = "agent_" + secrets.token_urlsafe(36)
    return key, hashlib.sha256(key.encode()).hexdigest()
