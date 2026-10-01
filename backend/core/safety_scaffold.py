import re
import json
from typing import List, Tuple
from core.llm_client import call_llm
from config import logger

# ---------------------------------------------------------------------------
# DOMAIN SAFETY PLACEHOLDERS
# FILL IN ONCE PROBLEM STATEMENT IS KNOWN AT THE HACKATHON
# Example for Health: [r"\b(chest pain|heart attack|fainted)\b"]
# Example for Fintech: [r"\b(cvv|otp|wire transfer|stolen card)\b"]
# Example for EdTech: [r"\b(cheat|exam leak|plagiarize)\b"]
# ---------------------------------------------------------------------------
DEFAULT_RED_FLAG_PATTERNS: List[str] = [
    r"\b((ignore|disregard)\s+(all\s+)?(previous|above|prior)\s+(instructions?|guidelines?|rules?))\b",
    r"\b(system\s+prompt\s+(override|reveal|leak))\b",
    r"\b(you\s+are\s+now\s+(in\s+developer\s+mode|dan))\b",
    r"\b(developer\s+mode\s+enabled)\b",
    r"\b(bypass\s+governor|disregard\s+policy)\b",
    r"\b(rm\s+-rf|drop\s+table|delete\s+from)\b",
]

DEFAULT_CLASSIFICATION_PROMPT = """You are a real-time safety and triage classifier.
Analyze the user's input for severe policy violations, emergencies, or high-risk requests.
# FILL IN DOMAIN SPECIFIC SAFETY RULES ONCE PROBLEM STATEMENT IS KNOWN

Respond ONLY with a JSON object:
{
  "is_flagged": true or false,
  "reason": "short explanation under 10 words"
}"""

def scan_for_flags(text: str, patterns: List[str] = None) -> Tuple[bool, str]:
    """Tier 0 Deterministic Safety Check (<5ms regex scan)."""
    active_patterns = patterns if patterns is not None else DEFAULT_RED_FLAG_PATTERNS
    if not text or not active_patterns:
        return False, ""

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
    classification_prompt: str = DEFAULT_CLASSIFICATION_PROMPT
) -> Tuple[bool, str]:
    """Tier 1 Semantic Safety Check via LLM JSON mode."""
    if not text or len(text.strip()) < 3:
        return False, ""

    res = call_llm(
        system_prompt=classification_prompt,
        user_prompt=f"User input: {text}",
        json_mode=True,
        temperature=0.0,
        max_tokens=150
    )

    if not res.success:
        if res.error == "SERVICE_UNAVAILABLE":
            logger.critical("Tier 1 safety check unreachable: SERVICE_UNAVAILABLE")
            return False, "SERVICE_UNAVAILABLE"
        return False, f"SAFETY_CHECK_ERROR: {res.error}"

    parsed = res.parsed_json or {}
    is_flagged = bool(parsed.get("is_flagged", False))
    reason = str(parsed.get("reason", ""))
    if is_flagged:
        logger.warning(f"Tier 1 Semantic Safety Flag triggered: {reason}")
    return is_flagged, reason
