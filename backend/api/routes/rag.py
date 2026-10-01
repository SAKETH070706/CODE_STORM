from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.repositories import DocumentRepository
from core.rag import (
    retrieve_context,
    index_knowledge_folder,
    index_document,
    delete_document,
    Chunk
)
import re
from pathlib import Path
from core.governor_identity import knowledge_admin
from integrations.pinecone_client import pinecone_service
from config import KNOWLEDGE_DIR, MAX_UPLOAD_SIZE_MB

router = APIRouter(tags=["Knowledge & Documents"])


class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=20)
    min_score: float = Field(default=0.05, ge=0.0, le=1.0)


class RagStatsResponse(BaseModel):
    status: str
    total_chunks: int
    dimension: int
    index_name: str
    namespace: str
    connected_to_pinecone: bool
    total_documents: int
    is_mock: bool


@router.get("/api/rag/stats", response_model=RagStatsResponse)
async def get_rag_stats(db: AsyncSession = Depends(get_db)):
    """Returns vector store metrics, Pinecone status, and document counts."""
    stats = pinecone_service.get_stats()
    doc_repo = DocumentRepository(db)
    doc_count = await doc_repo.count_all()

    return RagStatsResponse(
        status="ok",
        total_chunks=stats.get("total_vector_count", 0),
        dimension=stats.get("dimension", 1024),
        index_name=stats.get("index_name", "code-storm"),
        namespace=stats.get("namespace", "default"),
        connected_to_pinecone=stats.get("connected", False),
        total_documents=doc_count,
        is_mock=stats.get("is_mock", False)
    )


@router.post("/api/rag/query")
def direct_rag_query(req: RagQueryRequest):
    """Direct semantic similarity search returning top-K matching chunks."""
    chunks: List[Chunk] = retrieve_context(
        query=req.query,
        top_k=req.top_k,
        min_score=req.min_score
    )
    return {
        "status": "ok",
        "query": req.query,
        "count": len(chunks),
        "results": [c.to_dict() for c in chunks]
    }


@router.post("/api/rag/reindex")
@router.post("/api/rag/ingest")
async def trigger_rag_reindex(
    principal: Any = Depends(knowledge_admin),
    db: AsyncSession = Depends(get_db)
):
    """Triggers re-indexing of all documents in backend/data/knowledge/ into Pinecone & PostgreSQL."""
    doc_repo = DocumentRepository(db)
    result = await index_knowledge_folder(
        folder_path=str(KNOWLEDGE_DIR),
        doc_repo=doc_repo
    )
    return {
        "status": "success",
        "documents_processed": result["documents_processed"],
        "chunks_ingested": result["total_chunks"]
    }


@router.get("/api/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    """Lists all indexed knowledge documents from PostgreSQL."""
    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_all(limit=100)
    return {
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "content_hash": d.content_hash,
                "mime_type": d.mime_type,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "file_size": d.file_size,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat()
            }
            for d in docs
        ]
    }


@router.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    principal: Any = Depends(knowledge_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads a new document (.txt, .md), extracts text, indexes vectors to Pinecone,
    and records metadata in PostgreSQL.
    """
    raw_name = Path(file.filename or "uploaded_document.txt").name
    clean_name = raw_name.lstrip(".")
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid filename or path traversal attempt.")

    sanitized_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_name)
    allowed_exts = (".txt", ".md", ".json", ".csv")
    if not any(sanitized_name.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail=f"Unsupported file extension. Allowed: {', '.join(allowed_exts)}")

    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content_bytes = await file.read(max_bytes + 1024)
    if len(content_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum upload size of {MAX_UPLOAD_SIZE_MB}MB.")

    try:
        text_content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text.")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="File is empty.")

    # Save to local knowledge directory for persistence
    local_path = KNOWLEDGE_DIR / sanitized_name
    local_path.write_text(text_content, encoding="utf-8")

    doc_repo = DocumentRepository(db)
    doc_id, chunk_count = await index_document(
        name=sanitized_name,
        content=text_content,
        mime_type=file.content_type or "text/plain",
        doc_repo=doc_repo
    )

    return {
        "status": "success",
        "document_id": doc_id,
        "name": sanitized_name,
        "chunk_count": chunk_count
    }


@router.delete("/api/documents/{doc_id}")
async def delete_document_endpoint(
    doc_id: str,
    principal: Any = Depends(knowledge_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deletes document metadata from PostgreSQL and vectors from Pinecone."""
    doc_repo = DocumentRepository(db)
    success = await delete_document(doc_id=doc_id, doc_repo=doc_repo)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found or could not be deleted.")
    return {"status": "success", "message": f"Document '{doc_id}' and all associated vectors deleted."}
