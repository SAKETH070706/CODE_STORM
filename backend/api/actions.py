from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from governor.pipeline import GovernorPipeline
from governor.schemas import (
    ActionRequest,
    TrustedActionContext,
)

from execution.dispatcher import ExecutionDispatcher
from execution.persistence import (
    create_execution,
    complete_execution,
    fail_execution,
)

from governor.persistence import persist_action_decision

from approvals.service import create_approval

from storage.database import SessionLocal
from storage.models import Action


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api",
    tags=["Actions"],
)


# ============================================================
# REQUEST SCHEMA
# ============================================================

class ActionRequestBody(BaseModel):
    task_id: str
    tool: str
    resource: str
    arguments: Dict[str, Any] = Field(
        default_factory=dict
    )


# ============================================================
# TRUSTED DEMO IDENTITY
# ============================================================
#
# IMPORTANT:
# These values are assigned by the backend.
#
# The frontend/agent is NOT allowed to choose:
# - role
# - agent identity
# - provenance
# - environment
#

DEMO_AGENT_ID = "demo-data-analyst"
DEMO_ROLE = "data_analyst"
DEMO_TASK_SCOPE = "sales-report"
DEMO_PROVENANCE = "trusted_internal"
DEMO_ENVIRONMENT = "local"


# ============================================================
# HELPERS
# ============================================================

def safe_value(value: Any) -> Any:
    """
    Convert Enum-like objects into their underlying value.

    Example:
        Decision.ALLOW -> "ALLOW"

    Normal strings/numbers are returned unchanged.
    """

    if hasattr(value, "value"):
        return value.value

    return value


def risk_to_dict(risk: Any) -> Dict[str, Any]:
    """
    Convert RiskAssessment into a JSON-safe dictionary.
    """

    if risk is None:
        return {
            "score": 0,
            "level": "UNKNOWN",
            "factors": [],
        }

    score = getattr(
        risk,
        "score",
        0,
    )

    level = getattr(
        risk,
        "level",
        "UNKNOWN",
    )

    factors = getattr(
        risk,
        "factors",
        [],
    )

    return {
        "score": score,
        "level": safe_value(level),
        "factors": factors or [],
    }


def decision_to_string(decision: Any) -> str:
    """
    Convert Decision enum/string into uppercase string.
    """

    value = safe_value(decision)

    if value is None:
        return ""

    return str(value).upper()


def get_db():
    """
    Create a database session.
    """
    return SessionLocal()


# ============================================================
# POST /api/actions
# ============================================================

@router.post("/actions")
def evaluate_action(
    payload: ActionRequestBody,
):
    """
    Main Agent Permission Governor gateway.

    Flow:

        Request
          ↓
        Trusted Context
          ↓
        Governor
          ↓
        Persist Decision
          ↓
        ┌───────────┬────────────┬────────────┐
        │           │            │
       BLOCK      ESCALATE      ALLOW
        │           │            │
        ↓           ↓            ↓
       Audit     Approval      Executor
                                │
                                ↓
                             Outcome
    """

    db = get_db()

    try:

        # ====================================================
        # 1. BUILD ACTION REQUEST
        # ====================================================

        action_request = ActionRequest(
            task_id=payload.task_id,
            tool=payload.tool,
            resource=payload.resource,
            arguments=payload.arguments,
        )

        # ====================================================
        # 2. CREATE TRUSTED BACKEND CONTEXT
        # ====================================================

        context = TrustedActionContext(
            agent_id=DEMO_AGENT_ID,
            role=DEMO_ROLE,
            task_scope=DEMO_TASK_SCOPE,
            provenance=DEMO_PROVENANCE,
            environment=DEMO_ENVIRONMENT,
        )

        # ====================================================
        # 3. GOVERNOR EVALUATION
        # ====================================================
        #
        # IMPORTANT:
        # GovernorPipeline.evaluate() expects:
        #
        #     action=
        #     context=
        #
        # NOT request=.
        #

        pipeline = GovernorPipeline()

        decision = pipeline.evaluate(
            action=action_request,
            context=context,
        )

        # ====================================================
        # 4. NORMALIZE DECISION
        # ====================================================

        decision_name = decision_to_string(
            decision.decision
        )

        risk_data = risk_to_dict(
            decision.risk
        )

        # ====================================================
        # 5. PREPARE PERSISTENCE PAYLOAD
        # ====================================================

        decision_data = {
            "action_id": decision.action_id,
            "decision": decision_name,
            "reason": decision.reason,
            "risk_score": risk_data["score"],
            "risk_level": risk_data["level"],
            "risk_factors": risk_data["factors"],
            "requires_approval": decision.requires_approval,
            "latency_ms": decision.latency_ms,
        }

        # ====================================================
        # 6. PERSIST GOVERNOR DECISION
        # ====================================================
        #
        # IMPORTANT:
        # persist_action_decision() expects:
        #
        #     action_request=
        #     context=
        #     decision_response=
        #

        action_record = persist_action_decision(
            db=db,
            action_request=action_request,
            context=context,
            decision_response=decision_data,
        )

        # ====================================================
        # 7. BLOCK
        # ====================================================

        if decision_name == "BLOCK":

            db.commit()

            return {
                "action_id": decision.action_id,
                "decision": "BLOCK",
                "state": "BLOCKED",
                "reason": decision.reason,
                "risk": risk_data,
                "requires_approval": False,
                "latency_ms": decision.latency_ms,
            }

        # ====================================================
        # 8. ESCALATE
        # ====================================================

        if decision_name == "ESCALATE":

            approval = create_approval(
                db=db,
                action=action_record,
                requested_by=DEMO_AGENT_ID,
            )

            db.commit()

            return {
                "action_id": decision.action_id,
                "decision": "ESCALATE",
                "state": "PENDING_APPROVAL",
                "reason": decision.reason,
                "risk": risk_data,
                "requires_approval": True,
                "approval_id": approval.approval_id,
                "expires_at": approval.expires_at,
                "latency_ms": decision.latency_ms,
            }

        # ====================================================
        # 9. ALLOW
        # ====================================================

        if decision_name == "ALLOW":

            # ------------------------------------------------
            # Create execution record
            # ------------------------------------------------

            execution = create_execution(
                db=db,
                action_id=action_record.action_id,
            )

            db.commit()

            try:

                # --------------------------------------------
                # Restricted executor
                # --------------------------------------------

                dispatcher = ExecutionDispatcher()

                # IMPORTANT:
                #
                # Your actual dispatcher expects:
                #
                #     action=
                #     decision=
                #
                # It does NOT accept request= or context=.
                #

                result = dispatcher.execute(
                    action=action_request,
                    decision=decision,
                )

                # --------------------------------------------
                # Mark execution completed
                # --------------------------------------------

                complete_execution(
                    db=db,
                    execution=execution,
                    result=result,
                )

                db.commit()

                return {
                    "action_id": decision.action_id,
                    "decision": "ALLOW",
                    "state": "COMPLETED",
                    "reason": decision.reason,
                    "risk": risk_data,
                    "requires_approval": False,
                    "execution": result,
                    "latency_ms": decision.latency_ms,
                }

            except Exception as execution_error:

                # --------------------------------------------
                # Mark execution failed
                # --------------------------------------------

                fail_execution(
                    db=db,
                    execution=execution,
                    error=str(execution_error),
                )

                db.commit()

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Execution failed: "
                        f"{type(execution_error).__name__}: "
                        f"{execution_error}"
                    ),
                )

        # ====================================================
        # 10. UNKNOWN DECISION
        # ====================================================

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unknown governor decision: "
                f"{decision_name}"
            ),
        )

    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:
        db.rollback()
        raise

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Action gateway error: "
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )

    # ========================================================
    # CLOSE DATABASE
    # ========================================================

    finally:
        db.close()


# ============================================================
# POST /api/agent/run
# ============================================================

@router.post("/agent/run")
def agent_run(
    payload: ActionRequestBody,
):
    """
    Agent-facing alias for the action gateway.

    Currently uses the same governor pipeline.
    """

    return evaluate_action(payload)


# ============================================================
# GET /api/actions
# ============================================================

@router.get("/actions")
def list_actions(
    limit: int = 50,
):
    """
    Return recent governed actions.
    """

    db = get_db()

    try:

        actions = (
            db.query(Action)
            .order_by(
                Action.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "action_id": action.action_id,
                "task_id": action.task_id,
                "agent_id": action.agent_id,
                "tool": action.tool,
                "resource": action.resource,
                "decision": safe_value(
                    action.decision
                ),
                "state": safe_value(
                    action.state
                ),
                "reason": action.reason,
                "risk_score": action.risk_score,
                "risk_level": safe_value(
                    action.risk_level
                ),
                "created_at": action.created_at,
                "updated_at": getattr(
                    action,
                    "updated_at",
                    None,
                ),
            }
            for action in actions
        ]

    finally:
        db.close()


# ============================================================
# GET /api/actions/{action_id}
# ============================================================

@router.get("/actions/{action_id}")
def get_action(
    action_id: str,
):
    """
    Return one governed action.
    """

    db = get_db()

    try:

        action = (
            db.query(Action)
            .filter(
                Action.action_id == action_id
            )
            .first()
        )

        if action is None:

            raise HTTPException(
                status_code=404,
                detail="Action not found",
            )

        return {
            "action_id": action.action_id,
            "task_id": action.task_id,
            "agent_id": action.agent_id,
            "tool": action.tool,
            "resource": action.resource,
            "arguments": getattr(
                action,
                "arguments_json",
                None,
            ),
            "decision": safe_value(
                action.decision
            ),
            "state": safe_value(
                action.state
            ),
            "reason": action.reason,
            "risk_score": action.risk_score,
            "risk_level": safe_value(
                action.risk_level
            ),
            "requires_approval": getattr(
                action,
                "requires_approval",
                False,
            ),
            "created_at": action.created_at,
            "updated_at": getattr(
                action,
                "updated_at",
                None,
            ),
        }

    finally:
        db.close()