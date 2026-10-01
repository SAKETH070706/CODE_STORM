import sys
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from integrations.embeddings import EmbeddingService
from workspace.sources import _isolated
from core.rag import ingest_knowledge


def test_isolated_timeout_expired_converts_to_timeout_error():
    """Verify that subprocess.TimeoutExpired is captured and converted to standard TimeoutError."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["python"], timeout=12)
        with pytest.raises(TimeoutError) as exc_info:
            _isolated(content=b"test", extension=".txt")
        assert "timed out within 12 seconds" in str(exc_info.value)


def test_chroma_upsert_failure_handled_gracefully(tmp_path):
    """Verify that Chroma upsert exceptions do not crash ingest_knowledge and return 0."""
    folder = tmp_path / "docs"
    folder.mkdir()
    doc_file = folder / "policy.md"
    doc_file.write_text("## Test Section\nSome valid policy text content here.")

    mock_collection = MagicMock()
    mock_collection.upsert.side_effect = RuntimeError("Chroma SQLite database locked")

    with patch("core.rag.get_chroma_collection", return_value=mock_collection):
        res = ingest_knowledge(str(folder))
        assert res == 0
        assert mock_collection.upsert.called


def test_deterministic_embedding_handles_empty_text():
    """Verify that deterministic fallback embeddings produce a unit vector with norm 1.0 on empty string."""
    service = EmbeddingService(dimension=768)
    vec = service._deterministic_embed("")
    assert len(vec) == 768
    assert vec[0] == 1.0
    assert sum(x * x for x in vec) == pytest.approx(1.0)


def test_deterministic_embedding_handles_whitespace_text():
    """Verify that deterministic fallback embeddings produce a unit vector with norm 1.0 on whitespace string."""
    service = EmbeddingService(dimension=768)
    vec = service._deterministic_embed("   \n\t  ")
    assert len(vec) == 768
    assert vec[0] == 1.0
    assert sum(x * x for x in vec) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_503_exception_handler_includes_request_id():
    """Verify that safe_error exception handler in main.py includes request_id in body."""
    from api.main import safe_error
    from starlette.requests import Request
    import json

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/broken",
        "headers": [],
    }
    req = Request(scope)
    req.state.request_id = "req_audit_test_123"

    resp = await safe_error(req, RuntimeError("Simulated internal explosion"))
    assert resp.status_code == 503
    data = json.loads(resp.body.decode())
    assert data["request_id"] == "req_audit_test_123"
    assert "Service unavailable" in data["detail"]
