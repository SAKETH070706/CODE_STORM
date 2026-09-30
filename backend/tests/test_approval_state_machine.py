import pytest

from approvals.state_machine import can_transition, transition
from governor.schemas import ApprovalState


def test_pending_can_be_approved():
    assert can_transition(
        ApprovalState.PENDING,
        ApprovalState.APPROVED,
    )


def test_pending_can_be_rejected():
    assert can_transition(
        ApprovalState.PENDING,
        ApprovalState.REJECTED,
    )


def test_pending_can_expire():
    assert can_transition(
        ApprovalState.PENDING,
        ApprovalState.EXPIRED,
    )


def test_approved_can_be_revalidated():
    assert can_transition(
        ApprovalState.APPROVED,
        ApprovalState.REVALIDATED,
    )


def test_rejected_cannot_be_approved():
    assert not can_transition(
        ApprovalState.REJECTED,
        ApprovalState.APPROVED,
    )


def test_expired_cannot_be_approved():
    assert not can_transition(
        ApprovalState.EXPIRED,
        ApprovalState.APPROVED,
    )


def test_invalid_transition_raises():
    with pytest.raises(ValueError):
        transition(
            ApprovalState.REJECTED,
            ApprovalState.APPROVED,
        )