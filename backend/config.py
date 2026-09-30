# CODE_STORM Configuration
# Secrets are loaded exclusively from .env - NEVER hardcode API keys or credentials.
import os
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Logging Setup (Centralized)
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("code_storm_backend")

# ---------------------------------------------------------------------------
# API Credentials & Sanitizer
# ---------------------------------------------------------------------------
def _clean_str(val: str | None) -> str:
    """Detects and treats placeholder keys from .env.example as empty."""
    cleaned = (val or "").strip()
    if not cleaned or "your_" in cleaned.lower() or cleaned.startswith("gsk_your_") or cleaned.startswith("AIzaSy_your_") or cleaned.startswith("pcsk_your_"):
        return ""
    return cleaned

GROQ_API_KEY = _clean_str(os.getenv("GROQ_API_KEY", ""))
GEMINI_API_KEY = _clean_str(os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", ""))
PINECONE_API_KEY = _clean_str(os.getenv("PINECONE_API_KEY", ""))

# ---------------------------------------------------------------------------
# Database Configuration (Aiven PostgreSQL)
# ---------------------------------------------------------------------------
# Default to an async postgresql URL or async sqlite fallback for isolated testing
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@host:port/defaultdb?ssl=require"
).strip()

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_SSL_MODE = os.getenv("DB_SSL_MODE", "require").strip()

# ---------------------------------------------------------------------------
# Vector Database Configuration (Pinecone)
# ---------------------------------------------------------------------------
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "code-storm").strip()
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "default").strip()
PINECONE_HOST = os.getenv("PINECONE_HOST", "").strip()
PINECONE_METRIC = os.getenv("PINECONE_METRIC", "cosine").strip()

# Embedding model & provider
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "pinecone").strip().lower()
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "multilingual-e5-large").strip()
PINECONE_DIMENSION = int(os.getenv("PINECONE_DIMENSION", "1024"))

# ---------------------------------------------------------------------------
# LLM Providers & Failover Cascade
# ---------------------------------------------------------------------------
def _env_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or default

PRIMARY_LLM_PROVIDER = os.getenv("PRIMARY_LLM_PROVIDER", "groq").strip().lower()
PRIMARY_LLM_MODEL = os.getenv("PRIMARY_LLM_MODEL", "llama-3.3-70b-versatile").strip()
FALLBACK_LLM_PROVIDER = os.getenv("FALLBACK_LLM_PROVIDER", "gemini").strip().lower()
FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "gemini-2.5-flash").strip()

GROQ_MODELS = _env_list("GROQ_MODELS", [PRIMARY_LLM_MODEL, "llama-3.1-8b-instant"])
GROQ_VISION_MODELS = _env_list("GROQ_VISION_MODELS", ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"])
GEMINI_MODELS = _env_list("GEMINI_MODELS", [FALLBACK_LLM_MODEL, "gemini-1.5-flash", "gemini-1.5-pro"])

LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "25.0"))
MAX_RETRIES_PER_MODEL = int(os.getenv("MAX_RETRIES_PER_MODEL", "2"))

# ---------------------------------------------------------------------------
# Upload & Security Limits
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip() and origin.strip() != "*"
]

KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
