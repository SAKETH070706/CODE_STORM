import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from core.rag import (
    ingest_knowledge,
    retrieve,
    retrieve_context,
    chunk_document_content,
    compute_content_hash,
    index_document,
    delete_document,
    Chunk
)
from integrations.pinecone_client import pinecone_service


@pytest.mark.asyncio
async def test_ingest_nonexistent_or_empty_folder(tmp_path):
    count_missing = await ingest_knowledge(str(tmp_path / "does_not_exist"))
    assert count_missing == 0

    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    count_empty = await ingest_knowledge(str(empty_dir))
    assert count_empty == 0


def test_retrieve_empty_query():
    assert retrieve("") == []
    assert retrieve("   ") == []
    assert retrieve_context("") == []


def test_chunking_headings_and_sliding_window():
    md_content = """# Guidelines

## Authentication
Every request must include an authorization bearer token.

## Rate Limiting
Requests are limited to 100 requests per minute per IP.
"""
    chunks = chunk_document_content(md_content, "security.md")
    assert len(chunks) == 2
    assert "Authentication" in chunks[0]["section"]
    assert "Rate Limiting" in chunks[1]["section"]


def test_content_hashing_is_deterministic():
    text1 = "This is a test document."
    text2 = "This is a test document."
    text3 = "Different content."

    assert compute_content_hash(text1) == compute_content_hash(text2)
    assert compute_content_hash(text1) != compute_content_hash(text3)


@pytest.mark.asyncio
async def test_index_and_retrieve_end_to_end():
    content = "FastAPI with Pinecone enables high performance vector search in CODE_STORM."
    doc_id, count = await index_document(name="test_doc.txt", content=content)
    assert count >= 1

    # Query for relevant text
    results = retrieve_context("FastAPI Pinecone vector search", top_k=2, min_score=0.1)
    assert len(results) >= 1
    assert "test_doc.txt" in results[0].source_file
    assert results[0].score > 0.0

    # Delete document
    deleted = await delete_document(doc_id)
    assert deleted is True


def test_score_suppression_on_unrelated_query():
    # If minimum score is set very high (0.99) for an unrelated query, results are suppressed
    results = retrieve_context("astrophysics galaxies black holes", top_k=3, min_score=0.99)
    assert len(results) == 0
