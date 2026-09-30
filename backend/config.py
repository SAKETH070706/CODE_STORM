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

# ---------------------------------------------------------------------------
# Local Storage & Vector Database
# ---------------------------------------------------------------------------
CHROMA_DIR = BASE_DIR / "chroma_store"
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
CHROMA_COLLECTION_NAME = "code_storm_knowledge"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
