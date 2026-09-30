import time
import uuid

from .authorization import AuthorizationEngine
from .policy_loader import load_approval_rules
from .risk_engine import RiskEngine
from .schemas import (
    ActionRequest,
    ActionState,
    Decision,
    DecisionResponse,
    RiskAssessment,
    TrustedActionContext,
)
from .validators import validate_action_arguments


class GovernorPipeline:

    def __init__(self):

        self.authorization = (
            AuthorizationEngine()
        )

        self.risk_engine = RiskEngine()

        self.approval_rules = (
            load_approval_rules()
            .get("rules", {})
        )

    def evaluate(
        self,
        action: ActionRequest,
        context: TrustedActionContext,
    ) -> DecisionResponse:

        started = time.perf_counter()

        action_id = str(
            uuid.uuid4()
        )

        requested_action = (
            action.arguments.get(
                "action",
                "read",
            )
        )

        # ==========================================
        # TIER 0 — AUTHORIZATION
        # ==========================================

        authorized, reason = (
            self.authorization.authorize(
                role=context.role,
                task_id=action.task_id,
                tool=action.tool,
                resource=action.resource,
                action=requested_action,
            )
        )

        if not authorized:

            return self._response(
                action_id,
                Decision.BLOCK,
                ActionState.BLOCKED,
                reason,
                100,
                "BLOCKED_BY_POLICY",
                ["authorization_failure"],
                False,
                started,
            )

        # ==========================================
        # TIER 0 — ARGUMENT VALIDATION
        # ==========================================

        valid, reason = (
            validate_action_arguments(
                tool=action.tool,
                action=requested_action,
                arguments=action.arguments,
            )
        )

        if not valid:

            return self._response(
                action_id,
                Decision.BLOCK,
                ActionState.BLOCKED,
                reason,
                100,
                "BLOCKED_BY_VALIDATION",
                ["argument_validation_failure"],
                False,
                started,
            )

        # ==========================================
        # TIER 1 — RISK
        # ==========================================

        score, level, factors = (
            self.risk_engine.assess(
                tool=action.tool,
                action=requested_action,
                resource=action.resource,
                provenance=context.provenance,
                environment=context.environment,
                arguments=action.arguments,
            )
        )

        # ==========================================
        # CRITICAL
        # ==========================================

        if level == "CRITICAL":

            return self._response(
                action_id,
                Decision.BLOCK,
                ActionState.BLOCKED,
                "Critical-risk action blocked",
                score,
                level,
                factors,
                False,
                started,
            )

        # ==========================================
        # EXPLICIT APPROVAL POLICY
        # ==========================================

        approval_rule = (
            self.approval_rules
            .get(action.tool, {})
            .get(requested_action)
        )

        if approval_rule == "BLOCK":

            return self._response(
                action_id,
                Decision.BLOCK,
                ActionState.BLOCKED,
                "Action blocked by approval policy",
                score,
                level,
                factors,
                False,
                started,
            )

        if approval_rule == "ESCALATE":

            return self._response(
                action_id,
                Decision.ESCALATE,
                ActionState.PENDING_APPROVAL,
                "Human approval required",
                score,
                level,
                factors,
                True,
                started,
            )

        # ==========================================
        # HIGH RISK
        # ==========================================

        if level == "HIGH":

            return self._response(
                action_id,
                Decision.ESCALATE,
                ActionState.PENDING_APPROVAL,
                "High-risk action requires approval",
                score,
                level,
                factors,
                True,
                started,
            )

        # ==========================================
        # ALLOW
        # ==========================================

        return self._response(
            action_id,
            Decision.ALLOW,
            ActionState.ALLOWED,
            "Action allowed by runtime policy",
            score,
            level,
            factors,
            False,
            started,
        )

    @staticmethod
    def _response(
        action_id,
        decision,
        state,
        reason,
        score,
        level,
        factors,
        requires_approval,
        started,
    ):

        latency = (
            time.perf_counter() - started
        ) * 1000

        return DecisionResponse(
            action_id=action_id,
            decision=decision,
            state=state,
            reason=reason,
            risk=RiskAssessment(
                score=score,
                level=level,
                factors=factors,
            ),
            requires_approval=requires_approval,
            latency_ms=round(
                latency,
                3,
            ),
        )