import os
import glob
import hashlib
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    embedding_functions = None

from config import (
    CHROMA_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    logger
)
from integrations.embeddings import embedding_service
from integrations.pinecone_client import pinecone_service

@dataclass
class Chunk:
    text: str
    source_file: str
    distance: float = 0.0
    document_id: str = ""
    chunk_id: str = ""
    section: str = "General"
    score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_file": self.source_file,
            "distance": self.distance,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "section": self.section,
            "score": self.score
        }

_chroma_collection = None

def get_chroma_collection():
    """Initializes and returns the cached persistent Chroma collection with local embeddings."""
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    if chromadb is None:
        return None
    try:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME
        )
        _chroma_collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=emb_fn,
            metadata={"hnsw:space": "cosine"}
        )
        return _chroma_collection
    except Exception as e:
        logger.warning(f"Could not initialize Chroma collection: {e}")
        return None

def _chunk_text(content: str, filename: str, chunk_size: int = 600, overlap: int = 90) -> List[dict]:
    """Chunks by markdown H2 headings if present; falls back to sliding window chunking."""
    chunks = []
    if "## " in content:
        sections = content.split("\n## ")
        for i, sec in enumerate(sections):
            text = ("## " + sec if i > 0 else sec).strip()
            if len(text) > 20:
                chunks.append({"source_file": filename, "text": text})
        return chunks

    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        piece = content[start:end].strip()
        if piece:
            chunks.append({"source_file": filename, "text": piece})
        start += (chunk_size - overlap)
    return chunks

def ingest_knowledge(folder_path: str) -> int:
    """Reads all .md and .txt documents from folder, chunks, and upserts idempotently."""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        logger.warning(f"Knowledge folder does not exist: {folder_path}")
        return 0

    files = glob.glob(str(folder / "*.md")) + glob.glob(str(folder / "*.txt"))
    if not files:
        logger.info(f"No .md or .txt files found in {folder_path}. Ingestion skipped.")
        return 0

    all_chunks = []
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    all_chunks.extend(_chunk_text(content, Path(fpath).name))
        except Exception as e:
            logger.warning(f"Skipping unreadable file {fpath}: {e}")

    if not all_chunks:
        return 0

    collection = get_chroma_collection()
    if collection is None:
        logger.warning("Chroma collection unavailable; ingestion aborted.")
        return 0

    ids, docs, metas = [], [], []
    for c in all_chunks:
        unique_key = f"{c['source_file']}_{c['text']}"
        chunk_id = hashlib.sha256(unique_key.encode("utf-8")).hexdigest()[:16]
        ids.append(chunk_id)
        docs.append(c["text"])
        metas.append({"source_file": c["source_file"]})

    try:
        collection.upsert(ids=ids, documents=docs, metadatas=metas)
        logger.info(f"Ingested {len(ids)} unique chunks into Chroma collection '{CHROMA_COLLECTION_NAME}'.")
        return len(ids)
    except Exception as e:
        logger.error(f"Failed to upsert chunks into Chroma collection '{CHROMA_COLLECTION_NAME}': {e}")
        return 0

def retrieve(query: str, k: int = 4, max_distance: float = 0.70) -> List[Chunk]:
    """Queries Chroma for relevant chunks. Lower distance = more similar."""
    clean_q = query.strip()
    if not clean_q:
        return []

    collection = get_chroma_collection()
    if collection is None or collection.count() == 0:
        logger.info("Chroma collection is empty or uninitialized. Returning zero chunks.")
        return []

    try:
        res = collection.query(
            query_texts=[clean_q],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.warning(f"Chroma query failed: {e}")
        return []

    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    if not docs:
        return []

    if dists[0] > max_distance:
        logger.info(f"Best match distance ({dists[0]:.3f}) exceeds threshold ({max_distance}). Suppressing.")
        return []

    results = []
    for doc, meta, dist in zip(docs, metas, dists):
        if dist <= max_distance:
            results.append(Chunk(
                text=doc,
                source_file=meta.get("source_file", "unknown"),
                distance=round(float(dist), 4),
                document_id=meta.get("document_id", ""),
                chunk_id=meta.get("chunk_id", ""),
                section=meta.get("section", "General"),
                score=round(1.0 - float(dist), 4)
            ))
    return results


def retrieve_context(
    query: str,
    top_k: int = 4,
    min_score: float = 0.05,
    filter_dict: Optional[Dict[str, Any]] = None
) -> List[Chunk]:
    """
    Unified high-level retrieval pipeline:
    1. Embeds query using EmbeddingService (Pinecone Inference, Gemini, or deterministic fallback).
    2. Queries Pinecone vector store (or in-memory mock if unconfigured).
    3. If vector store is empty, falls back to local Chroma retrieval.
    4. Returns deduplicated and scored Chunk instances.
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    # 1. Query Pinecone vector store
    try:
        q_vec = embedding_service.embed_query(clean_q)
        matches = pinecone_service.query(
            query_vector=q_vec,
            top_k=top_k,
            filter_dict=filter_dict,
            min_score=min_score
        )
        if matches:
            chunks = []
            for m in matches:
                meta = m.get("metadata", {})
                chunks.append(Chunk(
                    text=meta.get("text", ""),
                    source_file=meta.get("source_file", "knowledge_base"),
                    distance=round(1.0 - m.get("score", 0.0), 4),
                    document_id=meta.get("document_id", ""),
                    chunk_id=m.get("id", ""),
                    section=meta.get("section", "General"),
                    score=m.get("score", 0.0)
                ))
            return chunks
    except Exception as e:
        logger.warning(f"Vector search retrieval failed ({e}), falling back to Chroma...")

    # 2. Fallback to Chroma
    chroma_chunks = retrieve(clean_q, k=top_k)
    return [
        Chunk(
            text=c.text,
            source_file=c.source_file,
            distance=c.distance,
            document_id=f"doc_{hashlib.md5(c.source_file.encode()).hexdigest()[:8]}",
            chunk_id=f"chk_{hashlib.md5(c.text.encode()).hexdigest()[:8]}",
            section="General",
            score=round(max(0.0, 1.0 - c.distance), 4)
        )
        for c in chroma_chunks
    ]


def index_document(document_id: str, filename: str, content: str) -> int:
    """
    Chunks, embeds, and indexes a single document into the active vector store.
    Returns the count of chunks indexed.
    """
    if not content or not content.strip():
        return 0

    raw_chunks = _chunk_text(content, filename)
    if not raw_chunks:
        return 0

    texts = [c["text"] for c in raw_chunks]
    vectors = embedding_service.embed_documents(texts)

    payloads = []
    for i, (chunk, vec) in enumerate(zip(raw_chunks, vectors)):
        chunk_id = f"doc_{document_id}_{i}"
        payloads.append({
            "id": chunk_id,
            "values": vec,
            "metadata": {
                "document_id": document_id,
                "source_file": filename,
                "chunk_index": i,
                "section": "General",
                "text": chunk["text"]
            }
        })

    pinecone_service.upsert_vectors(payloads)
    logger.info(f"Indexed {len(payloads)} chunks for document '{filename}' (ID: {document_id}).")
    return len(payloads)


def delete_document(document_id: str) -> bool:
    """Purges all vector embeddings for a given document."""
    return pinecone_service.delete_by_document(document_id)


def index_knowledge_folder(folder_path: str) -> int:
    """Ingests all files from folder into the active vector store."""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        logger.warning(f"Knowledge folder does not exist: {folder_path}")
        return 0

    files = glob.glob(str(folder / "*.md")) + glob.glob(str(folder / "*.txt"))
    total_indexed = 0
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    doc_id = hashlib.md5(Path(fpath).name.encode()).hexdigest()[:12]
                    count = index_document(doc_id, Path(fpath).name, content)
                    total_indexed += count
        except Exception as e:
            logger.warning(f"Failed to index knowledge file {fpath}: {e}")

    # Also sync with local Chroma if available
    try:
        ingest_knowledge(folder_path)
    except Exception:
        pass

    return total_indexed

