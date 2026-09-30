from __future__ import annotations

from typing import Any, Dict

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

from governor.persistence import (
    persist_action_decision,
)

from approvals.service import (
    create_approval,
)

from storage.database import SessionLocal

from .planner import AgentPlanner
from .schemas import (
    AgentTaskRequest,
)

# ============================================================
# CASE 8
# Semantic analysis layer
# ============================================================

from .semantic import SemanticAgentAnalyzer


# ============================================================
# TRUSTED AGENT IDENTITY
# ============================================================

DEMO_AGENT_ID = "demo-data-analyst"
DEMO_ROLE = "data_analyst"
DEMO_TASK_SCOPE = "sales-report"
DEMO_PROVENANCE = "trusted_internal"
DEMO_ENVIRONMENT = "local"


# ============================================================
# HELPERS
# ============================================================

def safe_value(value: Any) -> Any:

    if hasattr(value, "value"):
        return value.value

    return value


def risk_to_dict(
    risk: Any,
) -> Dict[str, Any]:

    if risk is None:
        return {
            "score": 0,
            "level": "UNKNOWN",
            "factors": [],
        }

    return {
        "score": getattr(
            risk,
            "score",
            0,
        ),
        "level": safe_value(
            getattr(
                risk,
                "level",
                "UNKNOWN",
            )
        ),
        "factors": getattr(
            risk,
            "factors",
            [],
        ) or [],
    }


# ============================================================
# AGENT WORKFLOW
# ============================================================

class AgentWorkflow:
    """
    Controlled Case 7 + Case 8 agent workflow.

    Case 7:
        User Task
            ↓
        Agent Planner
            ↓
        Action Proposal
            ↓
        Trusted Context
            ↓
        Governor
            ↓
        BLOCK / ALLOW / ESCALATE

    Case 8:
        User Instruction
            ↓
        Safety Scanner
            ↓
        RAG
            ↓
        LLM Semantic Analysis
            ↓
        Action Proposal
            ↓
        Case 7 Governor Pipeline

    IMPORTANT:
    The LLM NEVER makes the final authorization decision.
    The Governor remains authoritative.
    """

    def __init__(self):

        # ========================================================
        # CASE 7 COMPONENTS
        # ========================================================

        self.planner = AgentPlanner()

        self.governor = GovernorPipeline()

        self.dispatcher = ExecutionDispatcher()

        # ========================================================
        # CASE 8 COMPONENT
        # ========================================================

        self.semantic = SemanticAgentAnalyzer()

    # ============================================================
    # RUN WORKFLOW
    # ============================================================

    def run(
        self,
        task: AgentTaskRequest,
    ):

        db = SessionLocal()

        try:

            # =================================================
            # CASE 8 — SEMANTIC ANALYSIS
            # =================================================

            semantic_result = self.semantic.analyze(
                instruction=task.instruction,
                task_id=task.task_id,
            )

            # =================================================
            # CASE 8 — SAFETY BLOCK
            # =================================================

            if semantic_result["status"] == "blocked":

                return {
                    "task_id": task.task_id,
                    "action_id": "",
                    "decision": "BLOCK",
                    "state": "BLOCKED",
                    "reason": semantic_result["reason"],
                    "risk": {
                        "score": 100,
                        "level": "BLOCKED_BY_POLICY",
                        "factors": [
                            "safety_scanner"
                        ],
                    },
                    "requires_approval": False,
                    "approval_id": None,
                    "execution": None,
                    "latency_ms": 0.0,
                }

            # =================================================
            # CASE 8 — SEMANTIC FAILURE
            # =================================================

            if semantic_result["status"] == "error":

                raise RuntimeError(
                    semantic_result["reason"]
                )

            # =================================================
            # CASE 8 — EXTRACT LLM PROPOSAL
            # =================================================

            proposal_data = semantic_result[
                "proposal"
            ]

            # =================================================
            # CASE 7 — PLAN
            # =================================================

            proposal = self.planner.plan(
                task
            )

            # =================================================
            # CASE 8 — USE SEMANTIC PROPOSAL
            #
            # The LLM proposal is used only to construct
            # the proposed action.
            #
            # Governor still decides whether it is allowed.
            # =================================================

            proposal.tool = proposal_data.get(
                "tool",
                proposal.tool,
            )

            proposal.resource = proposal_data.get(
                "resource",
                proposal.resource,
            )

            proposal.arguments = proposal_data.get(
                "arguments",
                proposal.arguments,
            )

            # =================================================
            # CASE 7 — CONVERT PROPOSAL TO ACTION
            # =================================================

            action_request = ActionRequest(
                task_id=proposal.task_id,
                tool=proposal.tool,
                resource=proposal.resource,
                arguments=proposal.arguments,
            )

            # =================================================
            # CASE 7 — TRUSTED BACKEND CONTEXT
            # =================================================

            context = TrustedActionContext(
                agent_id=DEMO_AGENT_ID,
                role=DEMO_ROLE,
                task_scope=DEMO_TASK_SCOPE,
                provenance=DEMO_PROVENANCE,
                environment=DEMO_ENVIRONMENT,
            )

            # =================================================
            # CASE 7 — GOVERNOR
            # =================================================

            decision = self.governor.evaluate(
                action=action_request,
                context=context,
            )

            decision_name = safe_value(
                decision.decision
            )

            risk_data = risk_to_dict(
                decision.risk
            )

            # =================================================
            # CASE 7 — PERSIST DECISION
            # =================================================

            decision_data = {
                "action_id": decision.action_id,
                "decision": decision_name,
                "reason": decision.reason,
                "risk_score": risk_data["score"],
                "risk_level": risk_data["level"],
                "risk_factors": risk_data["factors"],
                "requires_approval": (
                    decision.requires_approval
                ),
                "latency_ms": decision.latency_ms,
            }

            action_record = persist_action_decision(
                db=db,
                action_request=action_request,
                context=context,
                decision_response=decision_data,
            )

            # =================================================
            # CASE 7 — BLOCK
            # =================================================

            if decision_name == "BLOCK":

                db.commit()

                return {
                    "task_id": task.task_id,
                    "action_id": decision.action_id,
                    "decision": "BLOCK",
                    "state": "BLOCKED",
                    "reason": decision.reason,
                    "risk": risk_data,
                    "requires_approval": False,
                    "approval_id": None,
                    "execution": None,
                    "latency_ms": decision.latency_ms,
                }

            # =================================================
            # CASE 7 — ESCALATE
            # =================================================

            if decision_name == "ESCALATE":

                approval = create_approval(
                    db=db,
                    action=action_record,
                    requested_by=DEMO_AGENT_ID,
                )

                db.commit()

                return {
                    "task_id": task.task_id,
                    "action_id": decision.action_id,
                    "decision": "ESCALATE",
                    "state": "PENDING_APPROVAL",
                    "reason": decision.reason,
                    "risk": risk_data,
                    "requires_approval": True,
                    "approval_id": approval.approval_id,
                    "execution": None,
                    "latency_ms": decision.latency_ms,
                }

            # =================================================
            # CASE 7 — ALLOW
            # =================================================

            if decision_name == "ALLOW":

                execution = create_execution(
                    db=db,
                    action_id=action_record.action_id,
                )

                db.commit()

                try:

                    result = self.dispatcher.execute(
                        action=action_request,
                        decision=decision,
                    )

                    complete_execution(
                        db=db,
                        execution=execution,
                        result=result,
                    )

                    db.commit()

                    return {
                        "task_id": task.task_id,
                        "action_id": decision.action_id,
                        "decision": "ALLOW",
                        "state": "COMPLETED",
                        "reason": decision.reason,
                        "risk": risk_data,
                        "requires_approval": False,
                        "approval_id": None,
                        "execution": result,
                        "latency_ms": decision.latency_ms,
                    }

                except Exception as execution_error:

                    fail_execution(
                        db=db,
                        execution=execution,
                        error=str(
                            execution_error
                        ),
                    )

                    db.commit()

                    raise

            # =================================================
            # UNKNOWN DECISION
            # =================================================

            db.rollback()

            raise RuntimeError(
                f"Unknown governor decision: "
                f"{decision_name}"
            )

        except Exception:

            db.rollback()

            raise

        finally:

            db.close()