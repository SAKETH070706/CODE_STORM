from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from config import GROQ_API_KEY, GEMINI_API_KEY, PINECONE_API_KEY
from db.database import check_database_health
from integrations.pinecone_client import pinecone_service

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health")
@router.get("/api/health")
def health_check():
    """Fast liveness check indicating that the API process is alive."""
    return {
        "status": "ok",
        "service": "code_storm_backend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/ready")
@router.get("/api/ready")
async def readiness_check():
    """
    Readiness check verifying critical infrastructure:
    - FastAPI API layer
    - Aiven PostgreSQL connection pool
    - Pinecone vector database
    - AI provider configuration
    """
    db_ok, db_msg = await check_database_health()
    pc_ok, pc_msg = pinecone_service.check_connection()

    has_llm = bool(GROQ_API_KEY or GEMINI_API_KEY)
    
    is_ready = db_ok
    status_str = "ready" if (is_ready and pc_ok and has_llm) else ("degraded" if is_ready else "not_ready")
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = {
        "status": status_str,
        "database": {
            "status": "connected" if db_ok else "unreachable",
            "provider": "Aiven PostgreSQL",
            "detail": db_msg
        },
        "vector_store": {
            "status": "connected" if pc_ok else ("fallback_mock" if not PINECONE_API_KEY else "error"),
            "provider": "Pinecone",
            "detail": pc_msg
        },
        "ai_providers": {
            "groq": "configured" if bool(GROQ_API_KEY) else "unconfigured",
            "gemini": "configured" if bool(GEMINI_API_KEY) else "unconfigured"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return JSONResponse(content=payload, status_code=status_code)
