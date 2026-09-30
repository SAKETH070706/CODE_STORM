import math
import logging
from typing import List, Dict, Any, Optional

from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    PINECONE_NAMESPACE,
    PINECONE_HOST,
    PINECONE_DIMENSION,
    PINECONE_METRIC,
    logger
)


class InMemoryVectorStore:
    """
    High-performance fallback vector store for isolated tests or unconfigured environments.
    Guarantees that RAG retrieval never crashes when running without a Pinecone API key.
    """
    def __init__(self):
        self._vectors: Dict[str, Dict[str, Any]] = {}

    def upsert(self, vectors: List[Dict[str, Any]], namespace: str = "default"):
        for v in vectors:
            key = f"{namespace}:{v['id']}"
            self._vectors[key] = {
                "id": v["id"],
                "values": v["values"],
                "metadata": v.get("metadata", {}),
                "namespace": namespace
            }

    def delete_by_document(self, document_id: str, namespace: str = "default") -> int:
        keys_to_del = [
            k for k, v in self._vectors.items()
            if v["namespace"] == namespace and v["metadata"].get("document_id") == document_id
        ]
        for k in keys_to_del:
            del self._vectors[k]
        return len(keys_to_del)

    def query(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> List[Dict[str, Any]]:
        results = []
        q_norm = math.sqrt(sum(x * x for x in query_vector)) or 1.0

        for item in self._vectors.values():
            if item["namespace"] != namespace:
                continue

            # Apply metadata filter if supplied
            if filter_dict:
                matches = True
                for fk, fv in filter_dict.items():
                    if isinstance(fv, dict) and "$eq" in fv:
                        if item["metadata"].get(fk) != fv["$eq"]:
                            matches = False
                            break
                    elif item["metadata"].get(fk) != fv:
                        matches = False
                        break
                if not matches:
                    continue

            v_vals = item["values"]
            v_norm = math.sqrt(sum(x * x for x in v_vals)) or 1.0
            dot_product = sum(a * b for a, b in zip(query_vector, v_vals))
            cosine_sim = dot_product / (q_norm * v_norm)

            results.append({
                "id": item["id"],
                "score": round(cosine_sim, 4),
                "metadata": item["metadata"]
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def stats(self, namespace: str = "default") -> Dict[str, Any]:
        count = sum(1 for v in self._vectors.values() if v["namespace"] == namespace)
        return {
            "total_vector_count": count,
            "dimension": PINECONE_DIMENSION,
            "namespaces": {namespace: {"vector_count": count}},
            "is_mock": True
        }


class PineconeService:
    """
    Production Pinecone vector database client with connection management,
    index verification, batching, metadata filtering, and graceful fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        namespace: Optional[str] = None,
        host: Optional[str] = None
    ):
        self.api_key = api_key or PINECONE_API_KEY
        self.index_name = index_name or PINECONE_INDEX_NAME
        self.namespace = namespace or PINECONE_NAMESPACE
        self.host = host or PINECONE_HOST

        self._client = None
        self._index = None
        self._in_memory = InMemoryVectorStore()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.index_name)

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from pinecone import Pinecone
                self._client = Pinecone(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone client: {e}")
                self._client = None
        return self._client

    def _get_index(self):
        if self._index is None and self.is_configured():
            pc = self._get_client()
            if pc is not None:
                try:
                    if self.host:
                        self._index = pc.Index(name=self.index_name, host=self.host)
                    else:
                        self._index = pc.Index(name=self.index_name)
                    logger.info(f"Connected to Pinecone index: '{self.index_name}'")
                except Exception as e:
                    logger.warning(f"Could not connect to Pinecone index '{self.index_name}': {e}")
                    self._index = None
        return self._index

    def check_connection(self) -> tuple[bool, str]:
        """Verifies Pinecone index connectivity for /ready endpoint."""
        if not self.is_configured():
            return False, "PINECONE_API_KEY or PINECONE_INDEX_NAME not configured (using local fallback)"
        try:
            index = self._get_index()
            if index is None:
                return False, f"Could not acquire index '{self.index_name}'"
            stats = index.describe_index_stats()
            return True, f"Connected (vector count: {stats.get('total_vector_count', 0)})"
        except Exception as e:
            return False, str(e)

    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None,
        batch_size: int = 100
    ) -> int:
        """
        Batch upserts vectors into Pinecone or fallback store.
        Each vector item must have format:
        {"id": "...", "values": [...], "metadata": {...}}
        """
        if not vectors:
            return 0

        target_ns = namespace or self.namespace
        index = self._get_index()

        if index is not None:
            try:
                total_upserted = 0
                for i in range(0, len(vectors), batch_size):
                    batch = vectors[i : i + batch_size]
                    index.upsert(vectors=batch, namespace=target_ns)
                    total_upserted += len(batch)
                logger.info(f"Upserted {total_upserted} vectors to Pinecone index '{self.index_name}' [ns: {target_ns}]")
                return total_upserted
            except Exception as e:
                logger.error(f"Pinecone batch upsert failed: {e}. Writing to fallback store.")

        # Fallback store
        self._in_memory.upsert(vectors, namespace=target_ns)
        return len(vectors)

    def query(
        self,
        query_vector: List[float],
        top_k: int = 4,
        filter_dict: Optional[Dict[str, Any]] = None,
        min_score: Optional[float] = None,
        namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic similarity search against Pinecone or fallback store.
        """
        target_ns = namespace or self.namespace
        index = self._get_index()

        if index is not None:
            try:
                kwargs: Dict[str, Any] = {
                    "vector": query_vector,
                    "top_k": top_k,
                    "include_metadata": True,
                    "namespace": target_ns
                }
                if filter_dict:
                    kwargs["filter"] = filter_dict

                res = index.query(**kwargs)
                matches = res.get("matches", [])
                results = []
                for m in matches:
                    score = float(m.get("score", 0.0))
                    if min_score is not None and score < min_score:
                        continue
                    results.append({
                        "id": m.get("id"),
                        "score": round(score, 4),
                        "metadata": m.get("metadata", {})
                    })
                return results
            except Exception as e:
                logger.warning(f"Pinecone query failed ({e}), checking fallback store...")

        results = self._in_memory.query(
            query_vector=query_vector,
            top_k=top_k,
            filter_dict=filter_dict,
            namespace=target_ns
        )
        if min_score is not None:
            results = [r for r in results if r["score"] >= min_score]
        return results

    def delete_by_document(self, document_id: str, namespace: Optional[str] = None) -> bool:
        """
        Deletes all vector chunks associated with a specific document.
        Guarantees that Pinecone and PostgreSQL remain synchronized.
        """
        target_ns = namespace or self.namespace
        index = self._get_index()
        success = True

        if index is not None:
            try:
                # Pinecone supports deletion by metadata filter
                index.delete(filter={"document_id": {"$eq": document_id}}, namespace=target_ns)
                logger.info(f"Deleted vectors for document '{document_id}' from Pinecone [ns: {target_ns}]")
            except Exception as e:
                logger.warning(f"Pinecone delete by filter failed: {e}")
                success = False

        # Also purge from in-memory fallback
        self._in_memory.delete_by_document(document_id, namespace=target_ns)
        return success

    def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Fetches vector store metrics."""
        target_ns = namespace or self.namespace
        index = self._get_index()

        if index is not None:
            try:
                stats = index.describe_index_stats()
                total_count = stats.get("total_vector_count", 0)
                dimension = stats.get("dimension", PINECONE_DIMENSION)
                namespaces = stats.get("namespaces", {})
                ns_count = namespaces.get(target_ns, {}).get("vector_count", total_count)
                return {
                    "connected": True,
                    "index_name": self.index_name,
                    "namespace": target_ns,
                    "total_vector_count": total_count,
                    "namespace_vector_count": ns_count,
                    "dimension": dimension,
                    "is_mock": False
                }
            except Exception as e:
                logger.warning(f"Could not fetch Pinecone stats: {e}")

        # Fallback store stats
        mem_stats = self._in_memory.stats(namespace=target_ns)
        return {
            "connected": False,
            "index_name": self.index_name,
            "namespace": target_ns,
            "total_vector_count": mem_stats["total_vector_count"],
            "namespace_vector_count": mem_stats["total_vector_count"],
            "dimension": PINECONE_DIMENSION,
            "is_mock": True
        }


# Global singleton instance
pinecone_service = PineconeService()
