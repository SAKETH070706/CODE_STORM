import glob
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import KNOWLEDGE_DIR, logger
from integrations.embeddings import embedding_service
from integrations.pinecone_client import pinecone_service


@dataclass
class Chunk:
    text: str
    source_file: str
    document_id: str
    chunk_id: str
    section: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_file": self.source_file,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "section": self.section,
            "score": self.score
        }


def compute_content_hash(content: str) -> str:
    """Computes deterministic SHA-256 hash of normalized content."""
    normalized = content.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def chunk_document_content(
    content: str,
    filename: str,
    chunk_size: int = 600,
    overlap: int = 90
) -> List[Dict[str, Any]]:
    """
    Intelligently chunks text by Markdown headers (H2/H3) when present,
    falling back to a sliding window with overlap.
    """
    clean_content = content.strip()
    if not clean_content:
        return []

    chunks: List[Dict[str, Any]] = []

    # Check for Markdown headers (## or ###)
    if re.search(r"^##+ ", clean_content, re.MULTILINE):
        sections = re.split(r"(^##+ .+)", clean_content, flags=re.MULTILINE)
        current_header = "Introduction"
        
        for part in sections:
            part = part.strip()
            if not part:
                continue
            if part.startswith("##"):
                current_header = part.lstrip("#").strip()
            else:
                # If section body is excessively long, apply sliding window chunking
                if len(part) > chunk_size * 2:
                    start = 0
                    c_idx = 0
                    while start < len(part):
                        end = min(start + chunk_size, len(part))
                        sub_text = part[start:end].strip()
                        if len(sub_text) > 20:
                            chunks.append({
                                "text": f"[{current_header}] {sub_text}",
                                "section": current_header,
                                "source_file": filename,
                                "sub_index": c_idx
                            })
                            c_idx += 1
                        start += (chunk_size - overlap)
                elif len(part) > 15:
                    chunks.append({
                        "text": f"[{current_header}] {part}",
                        "section": current_header,
                        "source_file": filename,
                        "sub_index": 0
                    })
        if chunks:
            return chunks

    # Fallback sliding window
    start = 0
    c_idx = 0
    while start < len(clean_content):
        end = min(start + chunk_size, len(clean_content))
        piece = clean_content[start:end].strip()
        if len(piece) > 15:
            chunks.append({
                "text": piece,
                "section": f"Part {c_idx + 1}",
                "source_file": filename,
                "sub_index": c_idx
            })
            c_idx += 1
        start += (chunk_size - overlap)

    return chunks


async def index_document(
    name: str,
    content: str,
    mime_type: str = "text/plain",
    doc_repo: Optional[Any] = None
) -> tuple[str, int]:
    """
    Indexes a document into Pinecone and records metadata in PostgreSQL.
    Deduplicates using SHA-256 content hash:
    - If hash exists and chunk count > 0, skips redundant vector embedding.
    - If modified or new, purges old vectors and upserts fresh chunks.
    """
    content_hash = compute_content_hash(content)
    raw_bytes_len = len(content.encode("utf-8"))

    # Check for existing document in database
    existing_doc = None
    if doc_repo is not None:
        try:
            existing_doc = await doc_repo.get_by_hash(content_hash)
        except Exception as e:
            logger.warning(f"Error checking existing document in db: {e}")

    # Generate document ID (deterministic based on hash)
    doc_id = existing_doc.id if existing_doc else f"doc_{content_hash[:16]}"

    # Chunk the content
    raw_chunks = chunk_document_content(content, name)
    if not raw_chunks:
        logger.warning(f"Document '{name}' produced 0 chunks.")
        return doc_id, 0

    # If document is already fully indexed and has chunks, skip re-embedding
    if existing_doc and existing_doc.chunk_count == len(raw_chunks) and existing_doc.status == "indexed":
        logger.info(f"Document '{name}' with hash '{content_hash[:8]}' already indexed. Skipping re-embedding.")
        return doc_id, existing_doc.chunk_count

    # Extract text from chunks for batch embedding
    texts_to_embed = [c["text"] for c in raw_chunks]
    embeddings = embedding_service.embed_documents(texts_to_embed)

    # Construct vector payloads for Pinecone
    vectors = []
    for idx, (chunk_data, emb) in enumerate(zip(raw_chunks, embeddings)):
        chunk_id = f"{doc_id}_{idx}"
        vectors.append({
            "id": chunk_id,
            "values": emb,
            "metadata": {
                "document_id": doc_id,
                "document_name": name,
                "chunk_id": chunk_id,
                "section": chunk_data["section"],
                "text": chunk_data["text"][:1000]  # Store clean passage text in metadata
            }
        })

    # Safely replace existing vectors for this document in Pinecone
    pinecone_service.delete_by_document(doc_id)
    upserted_count = pinecone_service.upsert_vectors(vectors)

    # Persist or update document record in PostgreSQL
    if doc_repo is not None:
        try:
            await doc_repo.create_or_update(
                name=name,
                content_hash=content_hash,
                chunk_count=len(vectors),
                file_size=raw_bytes_len,
                mime_type=mime_type,
                status="indexed",
                doc_id=doc_id
            )
        except Exception as e:
            logger.error(f"Failed to record document metadata in database: {e}")

    logger.info(f"Indexed document '{name}' ({len(vectors)} chunks) with ID '{doc_id}'.")
    return doc_id, len(vectors)


async def index_knowledge_folder(
    folder_path: Optional[str] = None,
    doc_repo: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Scans the knowledge directory for all .md and .txt files and indexes them idempotently.
    """
    target_dir = Path(folder_path) if folder_path else KNOWLEDGE_DIR
    if not target_dir.exists() or not target_dir.is_dir():
        logger.warning(f"Knowledge directory '{target_dir}' does not exist.")
        return {"documents_processed": 0, "total_chunks": 0}

    files = glob.glob(str(target_dir / "*.md")) + glob.glob(str(target_dir / "*.txt"))
    if not files:
        logger.info(f"No .md or .txt files found in '{target_dir}'.")
        return {"documents_processed": 0, "total_chunks": 0}

    docs_count = 0
    total_chunks = 0

    for fpath in files:
        try:
            path_obj = Path(fpath)
            content = path_obj.read_text(encoding="utf-8")
            if content.strip():
                _, count = await index_document(
                    name=path_obj.name,
                    content=content,
                    mime_type="text/markdown" if fpath.endswith(".md") else "text/plain",
                    doc_repo=doc_repo
                )
                docs_count += 1
                total_chunks += count
        except Exception as e:
            logger.error(f"Failed to read/index file '{fpath}': {e}")

    return {
        "documents_processed": docs_count,
        "total_chunks": total_chunks
    }


def retrieve_context(
    query: str,
    top_k: int = 4,
    min_score: float = 0.35,
    filter_dict: Optional[Dict[str, Any]] = None
) -> List[Chunk]:
    """
    RAG Query Retrieval Pipeline:
    1. Validates query.
    2. Embeds query via EmbeddingService.
    3. Searches Pinecone index.
    4. Filters results by relevance score.
    5. Returns grounded Chunk objects with source attribution.
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    # Generate query embedding
    q_vec = embedding_service.embed_query(clean_q)

    # Perform similarity search
    matches = pinecone_service.query(
        query_vector=q_vec,
        top_k=top_k,
        filter_dict=filter_dict,
        min_score=min_score
    )

    chunks: List[Chunk] = []
    for m in matches:
        meta = m.get("metadata", {})
        chunks.append(Chunk(
            text=meta.get("text", ""),
            source_file=meta.get("document_name", "Unknown"),
            document_id=meta.get("document_id", ""),
            chunk_id=meta.get("chunk_id", m.get("id", "")),
            section=meta.get("section", "General"),
            score=m.get("score", 0.0)
        ))

    return chunks


async def delete_document(doc_id: str, doc_repo: Optional[Any] = None) -> bool:
    """
    Deletes a document from PostgreSQL and purges its vectors from Pinecone,
    preventing orphaned vectors.
    """
    pinecone_service.delete_by_document(doc_id)
    if doc_repo is not None:
        try:
            return await doc_repo.delete_by_id(doc_id)
        except Exception as e:
            logger.error(f"Failed to delete document from database: {e}")
            return False
    return True


def retrieve(query: str, k: int = 4, max_distance: float = 0.70) -> List[Chunk]:
    """Compatibility wrapper converting max_distance to min_score."""
    min_score = max(0.0, 1.0 - max_distance)
    return retrieve_context(query, top_k=k, min_score=min_score)


async def ingest_knowledge(folder_path: str) -> int:
    """Compatibility wrapper for folder ingestion."""
    res = await index_knowledge_folder(folder_path)
    return res.get("total_chunks", 0)

