import math
import hashlib
import time
from typing import List, Optional

from config import (
    EMBEDDING_PROVIDER,
    EMBEDDING_MODEL_NAME,
    PINECONE_DIMENSION,
    PINECONE_API_KEY,
    GEMINI_API_KEY,
    logger
)


class EmbeddingService:
    """
    Centralized embedding service supporting:
    1. Pinecone Inference API (e.g. multilingual-e5-large)
    2. Google Gemini API (text-embedding-004)
    3. Deterministic pseudo-embedding for testing or offline environments
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        dimension: Optional[int] = None
    ):
        self.provider = (provider or EMBEDDING_PROVIDER).lower()
        self.model_name = model_name or EMBEDDING_MODEL_NAME
        self.dimension = dimension or PINECONE_DIMENSION
        self._pinecone_client = None
        self._gemini_client = None

    def _get_pinecone_client(self):
        if self._pinecone_client is None and PINECONE_API_KEY:
            try:
                from pinecone import Pinecone
                self._pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize Pinecone client for embeddings: {e}")
        return self._pinecone_client

    def _get_gemini_client(self):
        if self._gemini_client is None and GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client for embeddings: {e}")
        return self._gemini_client

    def _deterministic_embed(self, text: str) -> List[float]:
        """
        Generates a deterministic unit-normalized vector for testing or offline mode.
        Semantic overlap produces correlated projections via word hashing.
        """
        vec = [0.0] * self.dimension
        words = text.lower().split()
        if not words:
            vec[0] = 1.0
            return vec

        for word in words:
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        return vec

    def embed_documents(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        """Batch-embeds a list of document strings."""
        if not texts:
            return []

        clean_texts = [t.strip() for t in texts]

        # 1. Try Pinecone Inference
        if self.provider == "pinecone" and PINECONE_API_KEY:
            pc = self._get_pinecone_client()
            if pc is not None:
                try:
                    all_embeddings = []
                    for i in range(0, len(clean_texts), batch_size):
                        batch = clean_texts[i : i + batch_size]
                        # Use passage input_type for documents
                        res = pc.inference.embed(
                            model=self.model_name,
                            inputs=batch,
                            parameters={"input_type": "passage", "truncate": "END"}
                        )
                        for item in res:
                            values = getattr(item, "values", None) or item.get("values")
                            all_embeddings.append(values)
                    if all_embeddings and len(all_embeddings) == len(clean_texts):
                        return all_embeddings
                except Exception as e:
                    logger.warning(f"Pinecone inference embed failed ({e}), falling back...")

        # 2. Try Gemini Embeddings
        if (self.provider == "gemini" or GEMINI_API_KEY) and GEMINI_API_KEY:
            gc = self._get_gemini_client()
            if gc is not None:
                try:
                    all_embeddings = []
                    for i in range(0, len(clean_texts), batch_size):
                        batch = clean_texts[i : i + batch_size]
                        try:
                            res = gc.models.embed_content(
                                model="text-embedding-004",
                                contents=batch
                            )
                            if hasattr(res, "embeddings") and len(res.embeddings) == len(batch):
                                for emb in res.embeddings:
                                    all_embeddings.append(emb.values)
                                continue
                        except Exception:
                            pass

                        from concurrent.futures import ThreadPoolExecutor
                        def _embed_single(txt):
                            r = gc.models.embed_content(model="text-embedding-004", contents=txt)
                            if hasattr(r, "embeddings") and r.embeddings:
                                return r.embeddings[0].values
                            elif hasattr(r, "embedding") and r.embedding:
                                return r.embedding.values
                            return None

                        with ThreadPoolExecutor(max_workers=min(8, max(1, len(batch)))) as executor:
                            batch_results = list(executor.map(_embed_single, batch))
                            all_embeddings.extend([b for b in batch_results if b is not None])
                    if all_embeddings and len(all_embeddings) == len(clean_texts):
                        return all_embeddings
                except Exception as e:
                    logger.warning(f"Gemini embed failed ({e}), falling back to deterministic.")

        # 3. Fallback: Deterministic embedding (offline / test mode)
        return [self._deterministic_embed(t) for t in clean_texts]

    def embed_query(self, text: str) -> List[float]:
        """Embeds a single search query."""
        clean_text = text.strip()
        if not clean_text:
            return [0.0] * self.dimension

        # 1. Try Pinecone Inference with query input_type
        if self.provider == "pinecone" and PINECONE_API_KEY:
            pc = self._get_pinecone_client()
            if pc is not None:
                try:
                    res = pc.inference.embed(
                        model=self.model_name,
                        inputs=[clean_text],
                        parameters={"input_type": "query", "truncate": "END"}
                    )
                    first = res[0]
                    values = getattr(first, "values", None) or first.get("values")
                    if values:
                        return values
                except Exception as e:
                    logger.warning(f"Pinecone query embed failed ({e}), falling back...")

        # 2. Try Gemini Embeddings
        if (self.provider == "gemini" or GEMINI_API_KEY) and GEMINI_API_KEY:
            gc = self._get_gemini_client()
            if gc is not None:
                try:
                    res = gc.models.embed_content(
                        model="text-embedding-004",
                        contents=clean_text
                    )
                    if hasattr(res, "embeddings") and res.embeddings:
                        return res.embeddings[0].values
                    elif hasattr(res, "embedding") and res.embedding:
                        return res.embedding.values
                except Exception as e:
                    logger.warning(f"Gemini query embed failed ({e}), falling back to deterministic.")

        return self._deterministic_embed(clean_text)


# Global singleton instance
embedding_service = EmbeddingService()
