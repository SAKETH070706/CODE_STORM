import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from storage.models import Action

from audit.logger import record_event


def utc_now():
    return datetime.now(timezone.utc)


def decision_to_state(
    decision: str,
) -> str:
    """
    Convert Governor decision into persisted action state.
    """

    if decision == "ALLOW":
        return "ALLOWED"

    if decision == "BLOCK":
        return "BLOCKED"

    if decision == "ESCALATE":
        return "PENDING_APPROVAL"

    raise ValueError(
        f"Unknown decision: {decision}"
    )


def persist_action_decision(
    db: Session,
    action_request,
    context,
    decision_response: dict,
) -> Action:
    """
    Persist the Governor decision and create
    the initial audit trail.
    """

    action_id = decision_response["action_id"]

    decision = decision_response["decision"]

    state = decision_to_state(
        decision
    )

    risk_score = decision_response.get(
        "risk_score",
        0,
    )

    risk_level = decision_response.get(
        "risk_level",
        "UNKNOWN",
    )

    reason = decision_response.get(
        "reason",
        "",
    )

    requires_approval = decision_response.get(
        "requires_approval",
        False,
    )

    arguments_json = json.dumps(
        action_request.arguments,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )

    action = Action(
        action_id=action_id,
        task_id=action_request.task_id,
        agent_id=context.agent_id,
        tool=action_request.tool,
        resource=action_request.resource,
        arguments_json=arguments_json,
        decision=decision,
        state=state,
        risk_score=risk_score,
        risk_level=risk_level,
        reason=reason,
        requires_approval=requires_approval,
    )

    db.add(action)
    db.commit()
    db.refresh(action)

    # -----------------------------------------------------
    # AUDIT: ACTION RECEIVED
    # -----------------------------------------------------

    record_event(
        db=db,
        action_id=action.action_id,
        event_type="ACTION_RECEIVED",
        details={
            "task_id": action.task_id,
            "agent_id": action.agent_id,
            "tool": action.tool,
            "resource": action.resource,
        },
    )

    # -----------------------------------------------------
    # AUDIT: AUTHORIZATION CHECK
    # -----------------------------------------------------

    record_event(
        db=db,
        action_id=action.action_id,
        event_type="AUTHORIZATION_CHECK",
        details={
            "decision": decision,
            "reason": reason,
        },
    )

    # -----------------------------------------------------
    # AUDIT: RISK ASSESSMENT
    # -----------------------------------------------------

    record_event(
        db=db,
        action_id=action.action_id,
        event_type="RISK_ASSESSMENT",
        details={
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": decision_response.get(
                "risk_factors",
                [],
            ),
        },
    )

    # -----------------------------------------------------
    # AUDIT: FINAL DECISION
    # -----------------------------------------------------

    record_event(
        db=db,
        action_id=action.action_id,
        event_type="DECISION",
        details={
            "decision": decision,
            "state": state,
            "requires_approval": requires_approval,
            "latency_ms": decision_response.get(
                "latency_ms",
                0,
            ),
        },
    )

    return action