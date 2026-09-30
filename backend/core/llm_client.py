from typing import Optional, Dict, Any

from integrations.llm_service import (
    llm_service,
    LLMResult,
    clean_and_heal_json as _clean_and_heal_json,
    is_transient_error as _is_transient_error,
    GroqProvider,
    GeminiProvider
)
from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    GROQ_MODELS,
    GROQ_VISION_MODELS,
    GEMINI_MODELS,
    HTTP_TIMEOUT_SECONDS,
    MAX_RETRIES_PER_MODEL,
    logger
)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    json_mode: bool = False,
    max_tokens: int = 1500,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
    deadline_seconds: float = 25.0,
    request_id: Optional[str] = None
) -> LLMResult:
    """
    Main entry point for executing LLM requests across Groq and Gemini.
    """
    return llm_service.call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        json_mode=json_mode,
        max_tokens=max_tokens,
        image_bytes=image_bytes,
        mime_type=mime_type,
        deadline_seconds=deadline_seconds,
        request_id=request_id
    )
