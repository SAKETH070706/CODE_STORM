# Hackathon Starter Kit Configuration
# Secrets are loaded exclusively from .env - NEVER hardcode API keys or credentials.
import os
import logging
from pathlib import Path
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
# API Credentials (with Placeholder Sanitizer)
# ---------------------------------------------------------------------------
def _clean_api_key(val: str) -> str:
    """Detects and treats placeholder keys from .env.example as empty."""
    cleaned = (val or "").strip()
    if not cleaned or "your_" in cleaned.lower() or cleaned.startswith("gsk_your_") or cleaned.startswith("AIzaSy_your_"):
        return ""
    return cleaned

GROQ_API_KEY = _clean_api_key(os.getenv("GROQ_API_KEY", ""))
GEMINI_API_KEY = _clean_api_key(os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", ""))

# ---------------------------------------------------------------------------
# Provider Model Cascades (Overrideable from .env)
# ---------------------------------------------------------------------------
def _env_list(name: str, default: list) -> list:
    raw = os.getenv(name, "")
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items or default

# Explicit account-specific model IDs; no assumed model availability.
GROQ_MODELS = _env_list("GROQ_MODELS", [])
GROQ_VISION_MODELS = _env_list("GROQ_VISION_MODELS", [])
GEMINI_MODELS = _env_list("GEMINI_MODELS", [])
# ---------------------------------------------------------------------------
# Resilience & Timeout Policies
# ---------------------------------------------------------------------------
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "25.0"))
MAX_RETRIES_PER_MODEL = int(os.getenv("MAX_RETRIES_PER_MODEL", "2"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))

PRIMARY_LLM_PROVIDER = os.getenv("PRIMARY_LLM_PROVIDER", "groq")
PRIMARY_LLM_MODEL = os.getenv("PRIMARY_LLM_MODEL", "llama-3.3-70b-versatile")
FALLBACK_LLM_PROVIDER = os.getenv("FALLBACK_LLM_PROVIDER", "gemini")
FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Database Settings (Aiven PostgreSQL or local SQLite fallback)
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///code_storm.db")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_SSL_MODE = os.getenv("DB_SSL_MODE", "require")

# ---------------------------------------------------------------------------
# Vector Database & Embeddings (Pinecone / Chroma)
# ---------------------------------------------------------------------------
PINECONE_API_KEY = _clean_api_key(os.getenv("PINECONE_API_KEY", ""))
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "code-storm")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "default")
PINECONE_HOST = os.getenv("PINECONE_HOST", "")
PINECONE_DIMENSION = int(os.getenv("PINECONE_DIMENSION", "1024"))
PINECONE_METRIC = os.getenv("PINECONE_METRIC", "cosine")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "pinecone")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "multilingual-e5-large")

CHROMA_DIR = BASE_DIR / "chroma_store"
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
CHROMA_COLLECTION_NAME = "code_storm_knowledge"

# ---------------------------------------------------------------------------
# Security & Uploads
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")


def log_startup_diagnostics():
    """Logs non-sensitive provider and infrastructure readiness summary."""
    groq_status = "configured" if bool(GROQ_API_KEY) else "unconfigured"
    gemini_status = "configured" if bool(GEMINI_API_KEY) else "unconfigured"
    pinecone_status = "configured" if bool(PINECONE_API_KEY) else "unconfigured"
    db_scheme = DATABASE_URL.split("://")[0] if "://" in DATABASE_URL else "unknown"
    logger.info(
        f"Platform Initialization: Groq={groq_status}, Gemini={gemini_status}, "
        f"Pinecone={pinecone_status}, DatabaseScheme={db_scheme}"
    )

log_startup_diagnostics()

