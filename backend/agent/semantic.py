from __future__ import annotations

import json
import re
from typing import Any, Dict

from core.llm_client import call_llm
from core.rag import retrieve
from core.safety_scaffold import scan_for_flags


class SemanticAgentAnalyzer:
    """
    Case 8 semantic layer.

    Flow:
        Instruction
            ↓
        Safety Scan
            ↓
        RAG Retrieval
            ↓
        LLM Analysis
            ↓
        Structured Action Proposal

    IMPORTANT:
    This class NEVER executes an action and NEVER makes
    the final authorization decision.

    The Governor remains the final authority.
    """

    def analyze(
        self,
        instruction: str,
        task_id: str,
        k: int = 3,
        max_distance: float = 0.70,
    ) -> Dict[str, Any]:

        # =========================================================
        # 1. SAFETY SCAN
        # =========================================================

        is_flagged, trigger = scan_for_flags(instruction)

        if is_flagged:
            return {
                "status": "blocked",
                "reason": (
                    f"Suspicious instruction detected: "
                    f"{trigger}"
                ),
                "safety_flagged": True,
                "trigger": trigger,
            }

        # =========================================================
        # 2. RAG RETRIEVAL
        # =========================================================

        chunks = retrieve(
            instruction,
            k=k,
            max_distance=max_distance,
        )

        context = "\n\n".join(
            f"[{chunk.source_file}]\n{chunk.text}"
            for chunk in chunks
        )

        if not context:
            context = "No relevant policy context found."

        sources = list(
            dict.fromkeys(
                chunk.source_file
                for chunk in chunks
            )
        )

        # =========================================================
        # 3. LLM SEMANTIC ANALYSIS
        # =========================================================

        system_prompt = f"""
You are the semantic planning layer of an
Agent Permission Governor.

Your job is ONLY to convert the user's instruction
into a proposed agent action.

You MUST NOT authorize the action.
You MUST NOT execute anything.
The deterministic Governor makes the final decision.

Return ONLY valid JSON.

Required format:

{{
  "intent": "short description",
  "tool": "supported tool name",
  "resource": "target resource",
  "arguments": {{}},
  "reason": "why this action matches the instruction",
  "risk_hints": []
}}

Rules:
1. Do not invent credentials.
2. Do not invent permissions.
3. Do not bypass security policies.
4. Do not execute SQL directly.
5. Do not execute shell commands.
6. Prefer supported tools.
7. The Governor will make the final decision.
8. Never treat this response as authorization.

VERIFIED POLICY CONTEXT:

{context}
"""

        result = call_llm(
            system_prompt=system_prompt,
            user_prompt=instruction,
        )

        if not result.success:
            return {
                "status": "error",
                "reason": (
                    result.error
                    or "LLM analysis failed"
                ),
                "safety_flagged": False,
                "sources": sources,
            }

        # =========================================================
        # 4. SAFE JSON PARSING
        # =========================================================

        parsed = self._parse_json(result.text)

        if parsed is None:
            return {
                "status": "error",
                "reason": (
                    "LLM returned invalid "
                    "structured output"
                ),
                "provider_used": result.provider_used,
                "sources": sources,
            }

        return {
            "status": "ok",
            "proposal": parsed,
            "provider_used": result.provider_used,
            "sources": sources,
            "safety_flagged": False,
        }

    # =============================================================
    # JSON PARSER
    # =============================================================

    @staticmethod
    def _parse_json(
        text: str,
    ) -> Dict[str, Any] | None:

        # ---------------------------------------------------------
        # Basic type and empty-input validation
        # ---------------------------------------------------------

        if not isinstance(text, str):
            return None

        if not text.strip():
            return None

        cleaned = text.strip()

        # ---------------------------------------------------------
        # Remove ```json ... ``` wrapping
        # ---------------------------------------------------------

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        cleaned = cleaned.strip()

        # ---------------------------------------------------------
        # First attempt:
        # The COMPLETE response must be a JSON object.
        # ---------------------------------------------------------

        try:
            value = json.loads(cleaned)

            if isinstance(value, dict):
                return value

            # Reject arrays, strings, numbers, booleans, etc.
            #
            # Example rejected response:
            #
            # [
            #     {
            #         "tool": "database.read"
            #     }
            # ]

            return None

        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------
        # Second attempt:
        # Recover a JSON object from surrounding text.
        #
        # Example accepted:
        #
        # Here is the proposed action:
        # {"tool": "database.read"}
        #
        # Example rejected:
        #
        # [
        #     {"tool": "database.read"}
        # ]
        # ---------------------------------------------------------

        # If the response starts with an array, do not extract
        # an object from inside it.
        if cleaned.startswith("["):
            return None

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end <= start:
            return None

        candidate = cleaned[start:end + 1]

        try:
            value = json.loads(candidate)

            if isinstance(value, dict):
                return value

        except json.JSONDecodeError:
            return None

        return None