from governor.schemas import ApprovalState


ALLOWED_TRANSITIONS = {
    ApprovalState.PENDING: {
        ApprovalState.APPROVED,
        ApprovalState.REJECTED,
        ApprovalState.EXPIRED,
    },
    ApprovalState.APPROVED: {
        ApprovalState.REVALIDATED,
        ApprovalState.REVALIDATION_FAILED,
    },
    ApprovalState.REVALIDATED: set(),
    ApprovalState.REVALIDATION_FAILED: set(),
    ApprovalState.REJECTED: set(),
    ApprovalState.EXPIRED: set(),
}


def can_transition(
    current: ApprovalState,
    target: ApprovalState,
) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def transition(
    current: ApprovalState,
    target: ApprovalState,
) -> ApprovalState:

    if not can_transition(current, target):
        raise ValueError(
            f"Invalid approval transition: "
            f"{current.value} -> {target.value}"
        )

    return target