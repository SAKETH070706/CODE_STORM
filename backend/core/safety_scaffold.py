import re
from typing import List, Tuple, Optional
from core.llm_client import call_llm
from config import logger

# ---------------------------------------------------------------------------
# Tier 0 Deterministic Safety & Prompt Injection Patterns
# ---------------------------------------------------------------------------
SYSTEM_INJECTION_PATTERNS: List[str] = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|directives)",
    r"you\s+are\s+now\s+in\s+(developer|unrestricted|god)\s+mode",
    r"bypass\s+(all\s+)?(safety|security|filters)",
    r"output\s+(the\s+)?(system\s+prompt|initial\s+instructions)",
    r"reveal\s+(your\s+)?(system\s+prompt|api\s+key|credentials)",
    r"\b(dan|jailbreak)\s+mode\b",
]

DEFAULT_RED_FLAG_PATTERNS: List[str] = [
    # Domain specific emergency or safety patterns
    r"\b(suicide|self-harm|make a bomb|synthesize weapon)\b",
]

DEFAULT_CLASSIFICATION_PROMPT = """You are a real-time safety, policy and triage classifier.
Analyze the user's input for severe policy violations, harmful requests, security exploits, or illegal actions.

Respond ONLY with a JSON object:
{
  "is_flagged": true or false,
  "reason": "short explanation under 10 words"
}"""


def scan_for_flags(
    text: str,
    patterns: Optional[List[str]] = None,
    include_injection_defense: bool = True
) -> Tuple[bool, str]:
    """
    Tier 0 Deterministic Safety Check (<5ms regex scan).
    Scans for harmful patterns and prompt injection attempts.
    """
    if not text or not text.strip():
        return False, ""

    active_patterns = list(patterns) if patterns is not None else list(DEFAULT_RED_FLAG_PATTERNS)
    if include_injection_defense:
        active_patterns.extend(SYSTEM_INJECTION_PATTERNS)

    normalized = text.lower().strip()
    for pattern in active_patterns:
        match = re.search(pattern, normalized)
        if match:
            trigger = match.group(0)
            logger.warning(f"Tier 0 Safety Flag triggered: '{trigger}'")
            return True, trigger

    return False, ""


def semantic_check(
    text: str,
    classification_prompt: str = DEFAULT_CLASSIFICATION_PROMPT,
    request_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Tier 1 Semantic Safety Check via LLM JSON mode.
    """
    if not text or len(text.strip()) < 3:
        return False, ""

    res = call_llm(
        system_prompt=classification_prompt,
        user_prompt=f"User input to evaluate: {text}",
        json_mode=True,
        temperature=0.0,
        max_tokens=150,
        request_id=request_id
    )

    if not res.success:
        if res.error == "SERVICE_UNAVAILABLE":
            logger.critical(f"[{request_id or 'anon'}] Tier 1 safety check unreachable: SERVICE_UNAVAILABLE")
            return False, "SERVICE_UNAVAILABLE"
        return False, f"SAFETY_CHECK_ERROR: {res.error}"

    parsed = res.parsed_json or {}
    is_flagged = bool(parsed.get("is_flagged", False))
    reason = str(parsed.get("reason", ""))
    if is_flagged:
        logger.warning(f"[{request_id or 'anon'}] Tier 1 Semantic Safety Flag triggered: {reason}")
    return is_flagged, reason


def sanitize_context_for_rag(retrieved_text: str) -> str:
    """
    Sanitizes retrieved document text before feeding into LLM prompt
    to prevent retrieved documents from acting as prompt injection vectors.
    """
    if not retrieved_text:
        return ""
    # Strip potential prompt escaping markers
    clean = re.sub(r"(?i)(system\s+instruction:|system:|user:|\<\|im_start\|\>)", "", retrieved_text)
    return clean.strip()
