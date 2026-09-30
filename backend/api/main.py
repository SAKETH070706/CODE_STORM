import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# BACKEND ROOT
# -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# -------------------------------------------------------------------
# FASTAPI
# -------------------------------------------------------------------

from fastapi import (
    FastAPI,
    HTTPException,
    status,
    UploadFile,
    File,
)

from fastapi.middleware.cors import CORSMiddleware


# -------------------------------------------------------------------
# EXISTING CASE 1-5 / CORE IMPORTS
# -------------------------------------------------------------------

from config import KNOWLEDGE_DIR

from core.llm_client import call_llm

from core.rag import (
    retrieve,
    ingest_knowledge,
    get_chroma_collection,
)

from core.extraction import (
    extract_structured_data,
)

from core.safety_scaffold import (
    scan_for_flags,
)


# -------------------------------------------------------------------
# CASE 6 API ROUTERS
# -------------------------------------------------------------------

from api.actions import router as actions_router
from api.approvals import router as approvals_router
from api.audit import router as audit_router
from api.policies import router as policies_router


# -------------------------------------------------------------------
# CASE 7 API ROUTER
# -------------------------------------------------------------------

from api.agent import router as agent_router


# -------------------------------------------------------------------
# APPLICATION
# -------------------------------------------------------------------

app = FastAPI(
    title="CODE_STORM Agent Permission Governor",
    version="2.0.0",
    description=(
        "Runtime governance API for AI-agent "
        "actions with authorization, risk "
        "assessment, restricted execution, "
        "human approval and tamper-evident audit."
    ),
)


# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,

    # React/Vite frontend
    allow_origins=[
        "http://localhost:5173",
    ],

    allow_credentials=True,

    allow_methods=[
        "*",
    ],

    allow_headers=[
        "*",
    ],
)


# -------------------------------------------------------------------
# REGISTER CASE 6 ROUTERS
# -------------------------------------------------------------------

app.include_router(
    actions_router
)

app.include_router(
    approvals_router
)

app.include_router(
    audit_router
)

app.include_router(
    policies_router
)


# -------------------------------------------------------------------
# REGISTER CASE 7 AGENT ROUTER
# -------------------------------------------------------------------

app.include_router(
    agent_router
)


# ===================================================================
# EXISTING AI / TEXT-TO-TEXT API
# ===================================================================


class QueryRequest(BaseModel):

    query: str = Field(
        ...,
        min_length=1,
        description="User query or task",
    )

    user_context: Optional[str] = ""


class QueryResponse(BaseModel):

    status: str

    response: str

    provider_used: str

    sources: List[str] = Field(
        default_factory=list
    )


# ===================================================================
# EXISTING MULTIMODAL EXTRACTION
# ===================================================================


class DefaultExtractSchema(BaseModel):

    entity_name: str

    category: str

    key_points: List[str]

    confidence_score: float


class ExtractRequest(BaseModel):

    text: str = Field(
        ...,
        min_length=3,
    )


class ExtractResponse(BaseModel):

    status: str

    extracted: Optional[
        Dict[str, Any]
    ] = None

    error: Optional[str] = None


# ===================================================================
# HEALTH
# ===================================================================


@app.get(
    "/health",
    tags=["System"],
)
def health_check():

    return {
        "status": "ok",
        "service": "code_storm_backend",
        "governor": "active",
        "version": "2.0.0",
    }


# ===================================================================
# EXISTING TEXT -> TEXT
# ===================================================================


@app.post(
    "/api/process",
    response_model=QueryResponse,
    tags=["AI"],
)
def process_user_query(
    req: QueryRequest,
):
    """
    Existing AI copilot endpoint.

    Tier 0 safety scan
        ->
    Chroma retrieval
        ->
    LLM synthesis
    """

    # ---------------------------------------------------------------
    # 1. SAFETY SCAN
    # ---------------------------------------------------------------

    is_flagged, trigger = scan_for_flags(
        req.query
    )

    if is_flagged:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Security/Policy violation "
                f"triggered: '{trigger}'"
            ),
        )


    # ---------------------------------------------------------------
    # 2. VECTOR RETRIEVAL
    # ---------------------------------------------------------------

    chunks = retrieve(
        req.query,
        k=3,
        max_distance=0.70,
    )

    context_str = (
        "\n\n".join(
            [
                (
                    f"[{c.source_file}]:\n"
                    f"{c.text}"
                )
                for c in chunks
            ]
        )
        if chunks
        else
        "No relevant context found."
    )

    source_files = list(
        dict.fromkeys(
            [
                c.source_file
                for c in chunks
            ]
        )
    )


    # ---------------------------------------------------------------
    # 3. LLM
    # ---------------------------------------------------------------

    system_prompt = (
        "You are an intelligent hackathon "
        "solution assistant. "
        "Ground your advice strictly on "
        "verified context.\n\n"
        f"VERIFIED CONTEXT:\n"
        f"{context_str}"
    )

    result = call_llm(
        system_prompt=system_prompt,
        user_prompt=req.query,
    )

    if not result.success:

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "AI service temporarily "
                f"unavailable: {result.error}"
            ),
        )


    return QueryResponse(
        status="ok",
        response=result.text,
        provider_used=result.provider_used,
        sources=source_files,
    )


# ===================================================================
# EXISTING TEXT EXTRACTION
# ===================================================================


@app.post(
    "/api/extract",
    response_model=ExtractResponse,
    tags=["Multimodal"],
)
def extract_fields_endpoint(
    req: ExtractRequest,
):
    """
    Structured extraction from text.
    """

    result = extract_structured_data(
        schema=DefaultExtractSchema,
        text=req.text,
    )

    if (
        result.success
        and result.validated
    ):

        return ExtractResponse(
            status="success",
            extracted=(
                result.validated
                .model_dump()
            ),
        )


    return ExtractResponse(
        status="failed",
        error=result.error,
    )


# ===================================================================
# EXISTING IMAGE -> TEXT / STRUCTURED EXTRACTION
# ===================================================================


@app.post(
    "/api/extract/image",
    response_model=ExtractResponse,
    tags=["Multimodal"],
)
def extract_image_endpoint(
    file: UploadFile = File(...),
):
    """
    Multimodal extraction from image.
    """

    file_bytes = file.file.read()

    mime_type = (
        file.content_type
        or "image/png"
    )

    result = extract_structured_data(
        schema=DefaultExtractSchema,
        image_bytes=file_bytes,
        mime_type=mime_type,
    )

    if (
        result.success
        and result.validated
    ):

        return ExtractResponse(
            status="success",
            extracted=(
                result.validated
                .model_dump()
            ),
        )


    return ExtractResponse(
        status="failed",
        error=result.error,
    )


# ===================================================================
# EXISTING RAG INGEST
# ===================================================================


@app.post(
    "/api/rag/ingest",
    tags=["RAG"],
)
def trigger_rag_ingest():

    count = ingest_knowledge(
        str(KNOWLEDGE_DIR)
    )

    return {
        "status": "success",
        "chunks_ingested": count,
    }


# ===================================================================
# EXISTING RAG STATS
# ===================================================================


@app.get(
    "/api/rag/stats",
    tags=["RAG"],
)
def get_rag_stats():

    collection = (
        get_chroma_collection()
    )

    count = (
        collection.count()
        if collection
        else 0
    )

    return {
        "status": "ok",
        "total_chunks": count,
    }