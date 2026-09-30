import re
import json
import time
import base64
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    PRIMARY_LLM_PROVIDER,
    PRIMARY_LLM_MODEL,
    FALLBACK_LLM_PROVIDER,
    FALLBACK_LLM_MODEL,
    GROQ_MODELS,
    GROQ_VISION_MODELS,
    GEMINI_MODELS,
    LLM_TIMEOUT_SECONDS,
    LLM_MAX_RETRIES,
    logger
)


@dataclass
class LLMResult:
    success: bool
    text: str
    parsed_json: Optional[Dict[str, Any]] = None
    provider_used: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0


def is_transient_error(err_str: str) -> bool:
    """Returns True if error indicates temporary rate-limit, overload or timeout."""
    markers = ("429", "503", "rate limit", "rate_limit", "resource_exhausted", "unavailable", "timeout", "timed out", "overloaded")
    lower_err = err_str.lower()
    return any(m in lower_err for m in markers)


def clean_and_heal_json(raw_text: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Safely extracts and parses JSON from LLM output.
    Strips markdown code fences, handles whitespace, and repairs single truncated braces.
    NEVER uses eval().
    """
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return True, data, ""
        return True, {"data": data}, ""
    except json.JSONDecodeError:
        pass

    # Heuristic repair for single missing terminal brace
    repaired = text.rstrip()
    if not repaired.endswith("}"):
        last_brace = repaired.rfind("}")
        if last_brace != -1:
            repaired = repaired[:last_brace + 1]
        else:
            repaired += "}"
        try:
            data = json.loads(repaired)
            if isinstance(data, dict):
                return True, data, ""
        except Exception:
            pass

    return False, None, f"Failed to parse clean JSON from: {raw_text[:180]}"


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        json_mode: bool = False,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/png",
        timeout: float = 25.0,
        request_id: Optional[str] = None
    ) -> LLMResult:
        pass


class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._initial_api_key = api_key

    def get_api_key(self) -> str:
        import sys
        if "core.llm_client" in sys.modules:
            val = getattr(sys.modules["core.llm_client"], "GROQ_API_KEY", None)
            if val:
                return val
        import config
        return getattr(config, "GROQ_API_KEY", self._initial_api_key or "")

    def get_models(self, is_vision: bool) -> List[str]:
        import sys
        if "core.llm_client" in sys.modules:
            mod = sys.modules["core.llm_client"]
            if is_vision and hasattr(mod, "GROQ_VISION_MODELS") and getattr(mod, "GROQ_VISION_MODELS"):
                return getattr(mod, "GROQ_VISION_MODELS")
            if hasattr(mod, "GROQ_MODELS") and getattr(mod, "GROQ_MODELS"):
                return getattr(mod, "GROQ_MODELS")
        import config
        return config.GROQ_VISION_MODELS if is_vision else config.GROQ_MODELS

    def _get_client(self, timeout: float):
        from groq import Groq
        return Groq(api_key=self.get_api_key(), timeout=timeout, max_retries=0)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        json_mode: bool = False,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/png",
        timeout: float = 25.0,
        request_id: Optional[str] = None
    ) -> LLMResult:
        api_key = self.get_api_key()
        if not api_key:
            return LLMResult(success=False, text="", error="GROQ_API_KEY_UNSET")

        try:
            groq_client = self._get_client(timeout)
        except Exception as client_err:
            return LLMResult(success=False, text="", error=f"GROQ_CLIENT_INIT_FAILED: {client_err}")

        model_list = self.get_models(bool(image_bytes))
        start_time = time.monotonic()

        for model_id in model_list:
            for attempt in range(LLM_MAX_RETRIES + 1):
                elapsed = time.monotonic() - start_time
                remaining_time = max(1.0, timeout - elapsed)
                if remaining_time <= 1.0:
                    return LLMResult(success=False, text="", error="TIMEOUT", latency_ms=elapsed * 1000)

                try:
                    if image_bytes:
                        b64 = base64.b64encode(image_bytes).decode("utf-8")
                        user_content = [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}}
                        ]
                    else:
                        user_content = user_prompt

                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": user_content})

                    kwargs: Dict[str, Any] = {
                        "model": model_id,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "timeout": remaining_time,
                    }
                    if json_mode:
                        kwargs["response_format"] = {"type": "json_object"}

                    resp = groq_client.chat.completions.create(**kwargs)
                    raw_text = (resp.choices[0].message.content or "").strip()
                    total_latency = (time.monotonic() - start_time) * 1000

                    if json_mode:
                        ok, parsed, err = clean_and_heal_json(raw_text)
                        if not ok:
                            return LLMResult(
                                success=False,
                                text=raw_text,
                                provider_used=f"groq/{model_id}",
                                error=err,
                                latency_ms=total_latency
                            )
                        logger.info(f"[{request_id or 'anon'}] Served by Groq: {model_id} (JSON, {total_latency:.1f}ms)")
                        return LLMResult(
                            success=True,
                            text=raw_text,
                            parsed_json=parsed,
                            provider_used=f"groq/{model_id}",
                            latency_ms=total_latency
                        )

                    logger.info(f"[{request_id or 'anon'}] Served by Groq: {model_id} ({total_latency:.1f}ms)")
                    return LLMResult(
                        success=True,
                        text=raw_text,
                        provider_used=f"groq/{model_id}",
                        latency_ms=total_latency
                    )

                except Exception as err:
                    err_str = str(err)
                    total_latency = (time.monotonic() - start_time) * 1000
                    if is_transient_error(err_str) and attempt < LLM_MAX_RETRIES:
                        sleep_s = 0.5 * (2 ** attempt)
                        logger.warning(f"Groq {model_id} transient error ({err_str[:60]}), backing off {sleep_s}s...")
                        time.sleep(sleep_s)
                        continue
                    logger.warning(f"Groq {model_id} failed ({err_str[:80]}). Trying next model or fallback.")
                    break

        return LLMResult(
            success=False,
            text="",
            error="GROQ_PROVIDER_EXHAUSTED",
            latency_ms=(time.monotonic() - start_time) * 1000
        )


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._initial_api_key = api_key

    def get_api_key(self) -> str:
        import sys
        if "core.llm_client" in sys.modules:
            val = getattr(sys.modules["core.llm_client"], "GEMINI_API_KEY", None)
            if val:
                return val
        import config
        return getattr(config, "GEMINI_API_KEY", self._initial_api_key or "")

    def get_models(self) -> List[str]:
        import sys
        if "core.llm_client" in sys.modules:
            mod = sys.modules["core.llm_client"]
            if hasattr(mod, "GEMINI_MODELS") and getattr(mod, "GEMINI_MODELS"):
                return getattr(mod, "GEMINI_MODELS")
        import config
        return config.GEMINI_MODELS

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1500,
        json_mode: bool = False,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/png",
        timeout: float = 25.0,
        request_id: Optional[str] = None
    ) -> LLMResult:
        api_key = self.get_api_key()
        if not api_key:
            return LLMResult(success=False, text="", error="GEMINI_API_KEY_UNSET")

        from google import genai
        from google.genai import types

        start_time = time.monotonic()
        try:
            client = genai.Client(
                api_key=api_key,
                http_options={"timeout": max(1000, int(timeout * 1000))}
            )
        except Exception as client_err:
            return LLMResult(success=False, text="", error=f"GEMINI_CLIENT_INIT_FAILED: {client_err}")

        for gem_model in self.get_models():
            for attempt in range(LLM_MAX_RETRIES + 1):
                elapsed = time.monotonic() - start_time
                remaining_ms = max(1000, int((timeout - elapsed) * 1000))
                if (timeout - elapsed) <= 1.0:
                    return LLMResult(success=False, text="", error="TIMEOUT", latency_ms=elapsed * 1000)

                try:
                    contents = []
                    if image_bytes:
                        contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
                    contents.append(user_prompt)

                    config_kwargs: Dict[str, Any] = {
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    }
                    if system_prompt:
                        config_kwargs["system_instruction"] = system_prompt
                    if json_mode:
                        config_kwargs["response_mime_type"] = "application/json"

                    config = types.GenerateContentConfig(**config_kwargs)
                    resp = client.models.generate_content(
                        model=gem_model,
                        contents=contents,
                        config=config
                    )
                    raw_text = (resp.text or "").strip()
                    total_latency = (time.monotonic() - start_time) * 1000

                    if json_mode:
                        ok, parsed, err = clean_and_heal_json(raw_text)
                        if not ok:
                            return LLMResult(
                                success=False,
                                text=raw_text,
                                provider_used=f"gemini/{gem_model}",
                                error=err,
                                latency_ms=total_latency
                            )
                        logger.info(f"[{request_id or 'anon'}] Served by Gemini: {gem_model} (JSON, {total_latency:.1f}ms)")
                        return LLMResult(
                            success=True,
                            text=raw_text,
                            parsed_json=parsed,
                            provider_used=f"gemini/{gem_model}",
                            latency_ms=total_latency
                        )

                    logger.info(f"[{request_id or 'anon'}] Served by Gemini: {gem_model} ({total_latency:.1f}ms)")
                    return LLMResult(
                        success=True,
                        text=raw_text,
                        provider_used=f"gemini/{gem_model}",
                        latency_ms=total_latency
                    )

                except Exception as err:
                    err_str = str(err)
                    if is_transient_error(err_str) and attempt < LLM_MAX_RETRIES:
                        sleep_s = 0.5 * (2 ** attempt)
                        logger.warning(f"Gemini {gem_model} transient error ({err_str[:60]}), backing off {sleep_s}s...")
                        time.sleep(sleep_s)
                        continue
                    logger.warning(f"Gemini {gem_model} failed ({err_str[:80]}).")
                    break

        return LLMResult(
            success=False,
            text="",
            error="GEMINI_PROVIDER_EXHAUSTED",
            latency_ms=(time.monotonic() - start_time) * 1000
        )


class LLMService:
    """
    Orchestrates Primary LLM (Groq) with seamless failover to Fallback (Gemini).
    Provides centralized resilience, bounded retries, timeout management,
    JSON validation, and request ID propagation.
    """

    def __init__(self):
        self.groq_provider = GroqProvider()
        self.gemini_provider = GeminiProvider()

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        json_mode: bool = False,
        max_tokens: int = 1500,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/png",
        deadline_seconds: Optional[float] = None,
        request_id: Optional[str] = None
    ) -> LLMResult:
        timeout = min(deadline_seconds or LLM_TIMEOUT_SECONDS, 60.0)
        overall_start = time.monotonic()

        # Determine provider order based on config
        primary = self.groq_provider if PRIMARY_LLM_PROVIDER == "groq" else self.gemini_provider
        fallback = self.gemini_provider if PRIMARY_LLM_PROVIDER == "groq" else self.groq_provider

        # 1. Primary Provider Attempt
        if primary.get_api_key():
            res = primary.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                image_bytes=image_bytes,
                mime_type=mime_type,
                timeout=timeout,
                request_id=request_id
            )
            if res.success:
                return res
            logger.warning(f"[{request_id or 'anon'}] Primary provider ({PRIMARY_LLM_PROVIDER}) failed: {res.error}. Initiating fallback to {FALLBACK_LLM_PROVIDER}.")

        # 2. Fallback Provider Attempt
        remaining_timeout = max(2.0, timeout - (time.monotonic() - overall_start))
        if fallback.get_api_key():
            res = fallback.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                image_bytes=image_bytes,
                mime_type=mime_type,
                timeout=remaining_timeout,
                request_id=request_id
            )
            if res.success:
                return res
            logger.error(f"[{request_id or 'anon'}] Fallback provider ({FALLBACK_LLM_PROVIDER}) failed: {res.error}.")

        # 3. Both Providers Exhausted
        total_time = (time.monotonic() - overall_start) * 1000
        logger.critical(f"[{request_id or 'anon'}] All LLM providers exhausted. Returning controlled SERVICE_UNAVAILABLE.")
        return LLMResult(
            success=False,
            text="",
            error="SERVICE_UNAVAILABLE",
            latency_ms=total_time
        )


# Global singleton
llm_service = LLMService()
