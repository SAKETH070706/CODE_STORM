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
    import chromadb
    from sentence_transformers import SentenceTransformer
    from config import CHROMA_DIR, EMBEDDING_MODEL_NAME
    # Never download an embedding model implicitly. Operator must pre-provision its cache.
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
    collection = chromadb.PersistentClient(path=str(CHROMA_DIR)).get_or_create_collection("policy_" + org)
    segments = [(sid, data["revision"], segment) for sid, data in sources for segment in data["segments"]]
    if index and segments:
        texts = [item[2]["text"] for item in segments]
        collection.upsert(ids=[f"{sid}-{revision}-{segment['index']}" for sid, revision, segment in segments],
            documents=texts, embeddings=model.encode(texts).tolist(),
            metadatas=[{"source_id":sid,"revision":revision,"segment":seg["index"],"organization_id":org} for sid,revision,seg in segments])
    if not collection.count():
        return {"mode":"chroma", "passages":[]}
    result = collection.query(query_embeddings=model.encode([query]).tolist(),n_results=min(5,collection.count()),where={"organization_id":org})
    current = {(sid,rev,seg['index']):seg for sid,rev,seg in segments}
    hits=[]
    for text, meta in zip(result['documents'][0],result['metadatas'][0]):
        key=(meta['source_id'],meta['revision'],meta['segment'])
        if key in current and text == current[key]['text']:
            hits.append({**meta,"text":text,"supporting_only":True})
    return {"mode":"chroma", "passages":hits}
