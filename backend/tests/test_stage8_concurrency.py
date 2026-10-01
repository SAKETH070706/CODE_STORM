"""Tests for Stage 8 Concurrency, Performance & Resource Management."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from core.llm_client import _get_groq_client, _get_gemini_client
from core.rag import get_chroma_collection
from workspace.models import Database
from integrations.embeddings import EmbeddingService


def test_groq_client_singleton_reuse():
    """Verify that _get_groq_client reuses the existing client across calls."""
    with patch("core.llm_client.GROQ_API_KEY", "gsk_test_api_key_123456789"):
        with patch("groq.Groq") as mock_groq_class:
            mock_instance = MagicMock()
            mock_groq_class.return_value = mock_instance
            import core.llm_client as llm_mod
            llm_mod._groq_client = None

            c1 = _get_groq_client()
            c2 = _get_groq_client()

            assert c1 is c2
            assert mock_groq_class.call_count == 1
            llm_mod._groq_client = None


def test_chroma_collection_cached_singleton():
    """Verify that get_chroma_collection caches the collection object."""
    import core.rag as rag_mod
    mock_coll = MagicMock()
    rag_mod._chroma_collection = mock_coll

    assert get_chroma_collection() is mock_coll
    rag_mod._chroma_collection = None


def test_workspace_database_connection_pool_recycle(tmp_path):
    """Verify that Database engine configures connection recycling and pool bounds."""
    # Test with postgresql URL to verify connection pool configuration
    db = Database("postgresql+psycopg://user:pass@localhost:5432/testdb", testing=True)
    assert db.engine.pool._recycle == 1800
    assert db.engine.pool.size() == 10
    assert db.engine.pool._max_overflow == 20
    db.engine.dispose()


def test_embedding_service_deterministic_fallback():
    """Verify EmbeddingService produces deterministic normalized vectors."""
    svc = EmbeddingService(dimension=64)
    vec1 = svc.embed_query("sales report analysis")
    vec2 = svc.embed_query("sales report analysis")

    assert len(vec1) == 64
    assert vec1 == vec2
    # Ensure vector is normalized
    import math
    norm = math.sqrt(sum(x * x for x in vec1))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)
