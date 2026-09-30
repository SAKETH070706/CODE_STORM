from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from storage.database import (
    SessionLocal,
    init_db,
)

from storage.models import (
    Approval,
    Action,
)

from approvals.service import (
    get_approval,
    approve,
    reject,
    revalidate_approval,
)


router = APIRouter(
    prefix="/api",
    tags=["Approvals"],
)


class ApprovalDecisionRequest(BaseModel):

    decided_by: str = "demo-reviewer"

    reason: str | None = None


def serialize_action(action) -> dict[str, Any]:

    try:
        arguments = json.loads(
            action.arguments_json
        )
    except Exception:
        arguments = {}

    return {
        "action_id": action.action_id,
        "task_id": action.task_id,
        "agent_id": action.agent_id,
        "tool": action.tool,
        "resource": action.resource,
        "arguments": arguments,
        "decision": action.decision,
        "state": action.state,
        "risk_score": action.risk_score,
        "risk_level": action.risk_level,
        "reason": action.reason,
    }


def serialize_approval(
    approval,
    action=None,
):

    result = {
        "approval_id":
            approval.approval_id,

        "action_id":
            approval.action_id,

        "action_hash":
            approval.action_hash,

        "state":
            approval.state,

        "requested_by":
            approval.requested_by,

        "decided_by":
            approval.decided_by,

        "decision_reason":
            approval.decision_reason,

        "requested_at":
            approval.requested_at,

        "expires_at":
            approval.expires_at,

        "decided_at":
            approval.decided_at,
    }

    if action is not None:

        result["action"] = (
            serialize_action(action)
        )

    return result


# -------------------------------------------------------------------
# GET /api/approvals
# -------------------------------------------------------------------


@router.get("/approvals")
def list_approvals():

    init_db()

    db = SessionLocal()

    try:

        approvals = (
            db.query(Approval)
            .order_by(
                Approval.requested_at.desc()
            )
            .limit(100)
            .all()
        )

        result = []

        for approval in approvals:

            action = (
                db.query(Action)
                .filter(
                    Action.action_id
                    == approval.action_id
                )
                .first()
            )

            result.append(
                serialize_approval(
                    approval,
                    action,
                )
            )

        return {
            "count": len(result),
            "approvals": result,
        }

    finally:

        db.close()


# -------------------------------------------------------------------
# GET /api/approvals/{approval_id}
# -------------------------------------------------------------------


@router.get(
    "/approvals/{approval_id}"
)
def get_approval_endpoint(
    approval_id: str,
):

    init_db()

    db = SessionLocal()

    try:

        approval = get_approval(
            db,
            approval_id,
        )

        if approval is None:

            raise HTTPException(
                status_code=404,
                detail="Approval not found.",
            )

        action = (
            db.query(Action)
            .filter(
                Action.action_id
                == approval.action_id
            )
            .first()
        )

        return serialize_approval(
            approval,
            action,
        )

    finally:

        db.close()


# -------------------------------------------------------------------
# APPROVE
# -------------------------------------------------------------------


@router.post(
    "/approvals/{approval_id}/approve"
)
def approve_endpoint(
    approval_id: str,
    request: ApprovalDecisionRequest,
):

    init_db()

    db = SessionLocal()

    try:

        result = approve(
            db,
            approval_id,
            decided_by=request.decided_by,
            reason=(
                request.reason
                or "Approved by human reviewer"
            ),
        )

        action = (
            db.query(Action)
            .filter(
                Action.action_id
                == result.action_id
            )
            .first()
        )

        return serialize_approval(
            result,
            action,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    finally:

        db.close()


# -------------------------------------------------------------------
# REJECT
# -------------------------------------------------------------------


@router.post(
    "/approvals/{approval_id}/reject"
)
def reject_endpoint(
    approval_id: str,
    request: ApprovalDecisionRequest,
):

    init_db()

    db = SessionLocal()

    try:

        result = reject(
            db,
            approval_id,
            decided_by=request.decided_by,
            reason=(
                request.reason
                or "Rejected by human reviewer"
            ),
        )

        action = (
            db.query(Action)
            .filter(
                Action.action_id
                == result.action_id
            )
            .first()
        )

        return serialize_approval(
            result,
            action,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    finally:

        db.close()


# -------------------------------------------------------------------
# REVALIDATE
# -------------------------------------------------------------------


@router.post(
    "/approvals/{approval_id}/revalidate"
)
def revalidate_endpoint(
    approval_id: str,
):

    init_db()

    db = SessionLocal()

    try:

        result = revalidate_approval(
            db,
            approval_id,
        )

        action = (
            db.query(Action)
            .filter(
                Action.action_id
                == result.action_id
            )
            .first()
        )

        return serialize_approval(
            result,
            action,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    finally:

        db.close()