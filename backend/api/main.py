import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import Depends
# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from config import KNOWLEDGE_DIR, logger
from core.llm_client import call_llm

from core.extraction import extract_structured_data
from core.safety_scaffold import scan_for_flags

from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from core.governor_identity import get_principal, knowledge_admin, identities
from api.governor import router, governor, store
from api.routes.chat import router as chat_router
from api.limits import BodyLimit
from core.governor_runtime import process_lease

@asynccontextmanager
async def lifespan(app):
    identities()
    from core.governor_policy import load_policy
    load_policy()
    try:
        from db.database import init_db
        await init_db()
    except Exception as e:
        logger.warning(f"Copilot database init skipped or failed: {e}")
    with process_lease(store.path.with_suffix(".lock")):
        await run_in_threadpool(store.migrate)
        if not (await run_in_threadpool(store.verify))["valid"]:
            raise RuntimeError("Audit integrity check failed")
        await run_in_threadpool(governor.recover)
        yield
    try:
        from db.database import close_database
        await close_database()
    except Exception:
        pass
app = FastAPI(
    lifespan=lifespan,
    title="CODE_STORM AI Platform API",
    version="1.0.0",
    description="Resilient dual-provider LLM API with Chroma RAG and multimodal extraction."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[v.strip() for v in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if v.strip() and v.strip() != "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

class DefaultExtractSchema(BaseModel):
    entity_name: str
    category: str
    key_points: List[str]
    confidence_score: float

class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=16000)

class ExtractResponse(BaseModel):
    status: str
    extracted: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "code_storm_backend"}


@app.post("/api/extract", response_model=ExtractResponse)
def extract_fields_endpoint(req: ExtractRequest, principal=Depends(get_principal)):
    """Generic structured extraction endpoint from text with feedback retry."""
    res = extract_structured_data(schema=DefaultExtractSchema, text=req.text)
    if res.success and res.validated:
        return ExtractResponse(status="success", extracted=res.validated.model_dump())
    return ExtractResponse(status="failed", error="Extraction failed")

@app.post("/api/extract/image", response_model=ExtractResponse)
def extract_image_endpoint(file: UploadFile = File(...), principal=Depends(get_principal)):
    """Multimodal extraction from uploaded image using schema validation with retry."""
    file_bytes = file.file.read(2 * 1024 * 1024 + 1)
    if len(file_bytes) > 2 * 1024 * 1024:
        raise HTTPException(413, "Image too large")
    mime_type = file.content_type or "image/png"
    res = extract_structured_data(
        schema=DefaultExtractSchema,
        image_bytes=file_bytes,
        mime_type=mime_type
    )
    if res.success and res.validated:
        return ExtractResponse(status="success", extracted=res.validated.model_dump())
    return ExtractResponse(status="failed", error="Extraction failed")

@app.post("/api/rag/ingest")
def trigger_rag_ingest(principal=Depends(knowledge_admin)):
    """Triggers re-indexing of data/knowledge/ documents into local ChromaDB."""
    from core.rag import ingest_knowledge
    count = ingest_knowledge(str(KNOWLEDGE_DIR))
    return {"status": "success", "chunks_ingested": count}

@app.get("/api/rag/stats")
def get_rag_stats(principal=Depends(knowledge_admin)):
    """Returns vector store metrics and count of indexed chunks."""
    from core.rag import get_chroma_collection
    coll = get_chroma_collection()
    count = coll.count() if coll else 0
    return {"status": "ok", "total_chunks": count}

app.include_router(router)
app.include_router(chat_router)
app.add_middleware(BodyLimit)

@app.get("/ready")
def readiness():
    try:
        identities()
        with store.connection() as c:
            c.execute("SELECT version FROM schema_migrations").fetchone()
        if not governor.adapters.demo_path.is_file():
            raise RuntimeError()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Backend is not ready")

@app.exception_handler(Exception)
async def safe_error(request, exc):
    from starlette.responses import JSONResponse
    from config import logger
    logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse({"detail": "Service unavailable; no new execution is permitted without durable authorization."}, status_code=503)


# Rejected authenticated HTTP requests are audited without body/header content.
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from uuid import uuid4

async def rejected_request(request, code, detail):
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    try:
        principal = get_principal(HTTPAuthorizationCredentials(scheme=scheme, credentials=token)) if scheme.lower() == "bearer" and token else None
    except Exception:
        principal = None
    if principal is not None and 400 <= code < 500:
        rid = str(uuid4())
        def record():
            with store.connection(True) as c:
                store.append(c, {"request_id": rid, "principal_id": principal.principal_id, "role": principal.role,
                                 "decision": "BLOCK", "reason_code": "HTTP_" + str(code), "state": "BLOCKED",
                                 "policy_version": "http-boundary", "stage_timings": {}, "risk": None})
        try:
            await run_in_threadpool(record)
        except Exception:
            return JSONResponse({"detail": "Denial audit unavailable", "request_id": rid}, 503)
    return JSONResponse({"detail": detail}, code)

@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    response = await rejected_request(request, exc.status_code, exc.detail)
    if exc.headers:
        response.headers.update(exc.headers)
    return response

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return await rejected_request(request, 422, "Request does not match the strict schema")
