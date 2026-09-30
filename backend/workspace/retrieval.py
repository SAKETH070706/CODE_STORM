"""Supporting passages only; neither retrieval mode can create runtime permissions."""
import os
from workspace.models import Source, listed

def passages(db, org, query, index=False):
    with db.transaction(org) as s:
        sources = [(r.id, r.data) for r in listed(s, Source, org)]
    if os.getenv("WORKSPACE_POLICY_EMBEDDINGS", "false").lower() != "true":
        words = set(query.lower().split())
        hits = [{"source_id": sid, "revision": data["revision"], **segment, "supporting_only": True}
                for sid, data in sources for segment in data["segments"] if words & set(segment["text"].lower().split())]
        return {"mode": "lexical", "passages": hits[:5]}
    from integrations.embeddings import embedding_service
    from integrations.pinecone_client import pinecone_service
    segments = [(sid, data["revision"], segment) for sid, data in sources for segment in data["segments"]]
    if index and segments:
        texts = [item[2]["text"] for item in segments]
        embeddings = embedding_service.embed_documents(texts)
        vectors = [
            {
                "id": f"{sid}-{revision}-{segment['index']}",
                "values": emb,
                "metadata": {"source_id": sid, "revision": revision, "segment": segment["index"], "organization_id": org, "text": text}
            }
            for (sid, revision, segment), emb, text in zip(segments, embeddings, texts)
        ]
        pinecone_service.upsert_vectors(vectors, namespace=f"policy_{org}")
    
    q_vec = embedding_service.embed_query(query)
    matches = pinecone_service.query(q_vec, top_k=5, filter_dict={"organization_id": org}, namespace=f"policy_{org}")
    hits = []
    for m in matches:
        meta = m.get("metadata", {})
        hits.append({**meta, "text": meta.get("text", ""), "supporting_only": True})
    return {"mode": "pinecone", "passages": hits}
