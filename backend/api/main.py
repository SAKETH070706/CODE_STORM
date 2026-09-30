import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import CORS_ORIGINS, logger
from db.database import get_engine, close_database, get_session_factory
from db.models import Base
from db.repositories import DocumentRepository
from core.rag import index_knowledge_folder
from api.middleware import RequestIDMiddleware

from api.routes.health import router as health_router
from api.routes.chat import router as chat_router
from api.routes.extraction import router as extraction_router
from api.routes.rag import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan:
    1. Verifies database connectivity and ensures schema tables exist.
    2. Auto-indexes local knowledge directory on startup if database is empty.
    3. Gracefully closes connection pools on shutdown.
    """
    logger.info("Initializing CODE_STORM platform backend...")
    
    # 1. Initialize DB schema
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema synchronized successfully.")
    except Exception as e:
        logger.warning(f"Database schema auto-sync warning (migrations will manage this): {e}")

    # 2. Seed initial knowledge base if empty
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            doc_repo = DocumentRepository(session)
            doc_count = await doc_repo.count_all()
            if doc_count == 0:
                logger.info("No documents indexed. Ingesting initial knowledge documents...")
                await index_knowledge_folder(doc_repo=doc_repo)
                await session.commit()
    except Exception as e:
        logger.warning(f"Initial knowledge seeding skipped or failed: {e}")

    logger.info("CODE_STORM backend online and ready.")
    yield

    # Clean shutdown
    logger.info("Shutting down CODE_STORM platform backend...")
    await close_database()


app = FastAPI(
    lifespan=lifespan,
    title="CODE_STORM GenAI Hackathon Platform",
    version="2.0.0",
    description="Production-grade full-stack GenAI platform with Aiven PostgreSQL, Pinecone Vector DB, and resilient Groq/Gemini LLM cascade."
)

# 1. Request ID and Access Logging Middleware
app.add_middleware(RequestIDMiddleware)

try:
    from api.limits import BodyLimit
    app.add_middleware(BodyLimit)
except Exception:
    pass

async def rejected_request(request, code, detail):
    return _format_error_response(
        status_code=code,
        code=f"HTTP_{code}",
        message=detail,
        request_id=getattr(request.state, "request_id", "unknown")
    )


# 2. CORS Middleware with Preflight Support
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    expose_headers=["X-Request-ID"]
)

# ---------------------------------------------------------------------------
# Standard Error Response Format
# ---------------------------------------------------------------------------
def _format_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: Any = None
) -> JSONResponse:
    payload: Dict[str, Any] = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        },
        "request_id": request_id
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(
        content=payload,
        status_code=status_code,
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = getattr(request.state, "request_id", "unknown")
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        408: "REQUEST_TIMEOUT",
        413: "PAYLOAD_TOO_LARGE",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    detail_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _format_error_response(
        status_code=exc.status_code,
        code=error_code,
        message=detail_msg,
        request_id=req_id
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", "unknown")
    errors = exc.errors()
    clean_msg = "Validation failed for request fields."
    if errors:
        first_err = errors[0]
        field = ".".join(str(loc) for loc in first_err.get("loc", []))
        clean_msg = f"Field '{field}': {first_err.get('msg', 'invalid')}"
    return _format_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message=clean_msg,
        request_id=req_id,
        details=[{"field": ".".join(str(loc) for loc in e.get("loc", [])), "issue": e.get("msg")} for e in errors]
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{req_id}] Internal unhandled server error: {exc}", exc_info=True)
    return _format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred processing your request. Please contact support with the request ID.",
        request_id=req_id
    )


# Mount Core Platform Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(extraction_router)
app.include_router(rag_router)

# Optional governor router for governance compatibility
try:
    from api.governor import store, governor, router as governor_router
    app.include_router(governor_router)
except Exception:
    store = None
    governor = None


