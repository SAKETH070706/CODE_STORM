"""Tests for Stage 6 Security, Authentication, Authorization & Cryptographic Integrity."""
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi import HTTPException
from core.governor_store import Store
from workspace.audit import verify as verify_workspace_audit, append as append_workspace_audit
from workspace.identity import resolve as resolve_identity, token_for, MAX_SESSION_SECONDS, TOKEN_SECONDS, Identity
from core.governor_identity import get_principal


def test_checkpoint_spoofing_prevented_in_governor_store(tmp_path):
    """Ensure governor store verify() rejects checkpoints with missing or invalid fields."""
    db_path = tmp_path / "test_gov.db"
    store = Store(db_path)
    store.migrate()

    # Empty checkpoint dictionary should fail validation
    res = store.verify(checkpoint={})
    assert res["valid"] is False

    # Checkpoint with null fields should fail validation
    res_null = store.verify(checkpoint={"event_count": None, "head_hash": None})
    assert res_null["valid"] is False

    # Checkpoint with invalid event_count type should fail validation
    res_invalid_type = store.verify(checkpoint={"event_count": "one", "head_hash": "a" * 64})
    assert res_invalid_type["valid"] is False

    # Valid verify without checkpoint passes
    res_none = store.verify(checkpoint=None)
    assert res_none["valid"] is True


def test_checkpoint_spoofing_prevented_in_workspace_audit():
    """Ensure workspace audit verify() rejects checkpoints with missing or invalid fields."""
    mock_session = MagicMock()
    mock_org = MagicMock()
    mock_org.audit_sequence = 0
    mock_org.audit_head = "0" * 64
    mock_session.get.return_value = mock_org
    mock_session.scalars.return_value = []

    # Checkpoint with missing event_count/head_hash should fail
    res = verify_workspace_audit(mock_session, "org-1", checkpoint={"organization_id": "org-1"})
    assert res["valid"] is False

    # Checkpoint with None values should fail
    res_null = verify_workspace_audit(mock_session, "org-1", checkpoint={"organization_id": "org-1", "event_count": None, "head_hash": None})
    assert res_null["valid"] is False


def test_governor_identity_misconfigured_returns_503():
    """Ensure get_principal returns 503 instead of uncaught 500 when tokens are misconfigured."""
    with patch("core.governor_identity.identities", side_effect=RuntimeError("Tokens missing")):
        mock_creds = MagicMock()
        mock_creds.credentials = "test-token"
        with pytest.raises(HTTPException) as exc_info:
            get_principal(mock_creds)
        assert exc_info.value.status_code == 503
        assert "misconfigured" in exc_info.value.detail.lower()


def test_agent_token_missing_record_raises_401():
    """Ensure resolving an agent token with a non-existent or inactive agent raises 401, not 404."""
    mock_session = MagicMock()
    mock_credential = MagicMock()
    mock_credential.organization_id = "org-123"
    mock_credential.agent_id = "agent-456"
    mock_credential.active = True
    # Credential exists, but agent record is None
    mock_session.scalar.side_effect = [mock_credential, None]

    with pytest.raises(HTTPException) as exc_info:
        resolve_identity(mock_session, "agent_secret_token_12345678901234567890")
    assert exc_info.value.status_code == 401
    assert "revoked or unavailable" in exc_info.value.detail.lower()
