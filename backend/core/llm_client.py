import re
import json
import time
import base64
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

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

@dataclass
class LLMResult:
    success: bool
    text: str
    parsed_json: Optional[Dict[str, Any]] = None
    provider_used: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0

def _is_transient_error(err_str: str) -> bool:
    """Returns True if error code or message indicates a temporary capacity/rate issue."""
    markers = ("429", "503", "rate limit", "rate_limit", "resource_exhausted", "unavailable", "timeout", "timed out")
    lower_err = err_str.lower()
    return any(m in lower_err for m in markers)

def _clean_and_heal_json(raw_text: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Strips markdown code fences and attempts at most one heuristic repair for truncated braces or brackets.
    Fails loud if valid JSON cannot be restored to protect data correctness.
    """
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return True, data, ""
        return True, {"data": data}, ""
    except json.JSONDecodeError:
        pass

    repaired = text.rstrip()
    if repaired.startswith("["):
        if not repaired.endswith("]"):
            last_brace = repaired.rfind("}")
            if last_brace != -1:
                repaired = repaired[:last_brace + 1].rstrip().rstrip(",") + "]"
            else:
                last_comma = repaired.rfind(",")
                if last_comma != -1:
                    repaired = repaired[:last_comma].rstrip() + "]"
                else:
                    repaired += "]"
        try:
            data = json.loads(repaired)
            return True, {"data": data} if not isinstance(data, dict) else data, ""
        except Exception:
            pass
    else:
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
            return True, {"data": data}, ""
        except Exception:
            pass

    return False, None, f"Failed to parse clean JSON: {raw_text[:200]}"

def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    json_mode: bool = False,
    max_tokens: int = 1000,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
    deadline_seconds: float = 15.0,
    request_id: Optional[str] = None
) -> LLMResult:
    """
    Executes an LLM call across Groq with automatic cascade to Gemini.
    Retries only on transient errors (429/503/timeout), with capped backoff.
    """
    req_tag = f"[{request_id}] " if request_id else ""
    call_start = time.monotonic()
    _LLMResult = globals()["LLMResult"]

    def LLMResult(**kwargs):
        if "duration_ms" not in kwargs:
            kwargs["duration_ms"] = round((time.monotonic() - call_start) * 1000, 1)
        return _LLMResult(**kwargs)

    deadline = time.monotonic() + min(max(deadline_seconds, 0.01), 60.0)
    def remaining():
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("Overall provider deadline exhausted")
        return min(HTTP_TIMEOUT_SECONDS, left)

    # 1. Tier 1: Groq Cascade
    if GROQ_API_KEY:
        try:
            from groq import Groq
            groq_client = Groq(api_key=GROQ_API_KEY, timeout=remaining(), max_retries=0)
            groq_model_list = GROQ_VISION_MODELS if image_bytes else GROQ_MODELS

            for model_id in groq_model_list:
                if time.monotonic() >= deadline:
                    return LLMResult(success=False, text="", error="DEADLINE_EXCEEDED")
                for attempt in range(MAX_RETRIES_PER_MODEL):
                    try:
                        if image_bytes:
                            b64 = base64.b64encode(image_bytes).decode("utf-8")
                            user_content = [
                                {"type": "text", "text": user_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}}
                            ]
                        else:
                            user_content = user_prompt

                        kwargs: Dict[str, Any] = {
                            "model": model_id,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_content}
                            ],
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        }
                        if json_mode:
                            kwargs["response_format"] = {"type": "json_object"}

                        kwargs["timeout"] = remaining()
                        resp = groq_client.chat.completions.create(**kwargs)
                        raw_text = (resp.choices[0].message.content or "").strip()

                        if json_mode:
                            ok, parsed, err = _clean_and_heal_json(raw_text)
                            if not ok:
                                return LLMResult(
                                    success=False,
                                    text=raw_text,
                                    provider_used=f"groq/{model_id}",
                                    error=err
                                )
                            logger.info(f"Served by Groq model: {model_id} (JSON)")
                            return LLMResult(
                                success=True,
                                text=raw_text,
                                parsed_json=parsed,
                                provider_used=f"groq/{model_id}"
                            )

                        logger.info(f"Served by Groq model: {model_id}")
                        return LLMResult(
                            success=True,
                            text=raw_text,
                            provider_used=f"groq/{model_id}"
                        )

                    except TimeoutError as timeout_err:
                        logger.warning(f"Groq {model_id} deadline exceeded: {timeout_err}")
                        return LLMResult(
                            success=False,
                            text="",
                            provider_used=f"groq/{model_id}",
                            error="DEADLINE_EXCEEDED"
                        )
                    except Exception as err:
                        err_str = str(err)
                        if "deadline exhausted" in err_str.lower():
                            return LLMResult(
                                success=False,
                                text="",
                                provider_used=f"groq/{model_id}",
                                error="DEADLINE_EXCEEDED"
                            )
                        if _is_transient_error(err_str) and attempt < (MAX_RETRIES_PER_MODEL - 1):
                            sleep_time = 0.5 * (attempt + 1)
                            logger.warning(f"Groq {model_id} transient error ({err_str[:80]}), retrying in {sleep_time}s...")
                            try:
                                rem = remaining()
                            except TimeoutError:
                                return LLMResult(success=False, text="", error="DEADLINE_EXCEEDED")
                            time.sleep(min(sleep_time, rem))
                            continue
                        logger.warning(f"Groq {model_id} failed: {err_str[:120]}. Failing to next model.")
                        break
        except TimeoutError:
            return LLMResult(success=False, text="", error="DEADLINE_EXCEEDED")
        except Exception as client_err:
            logger.warning(f"Groq client init failed: {client_err}")

    if time.monotonic() >= deadline:
        return LLMResult(success=False, text="", error="DEADLINE_EXCEEDED")

    # 2. Tier 2: Gemini Cascade Fallback
    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types

            g_client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options={"timeout": int(remaining() * 1000)}  # google-genai expects milliseconds
            )

            for gem_model in GEMINI_MODELS:
                if time.monotonic() >= deadline:
                    return LLMResult(success=False, text="", error="DEADLINE_EXCEEDED")
                for attempt in range(MAX_RETRIES_PER_MODEL):
                    try:
                        contents = []
                        if image_bytes:
                            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
                        
                        contents.append(user_prompt)

                        config_args: Dict[str, Any] = {
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                            "system_instruction": system_prompt,
                        }
                        if json_mode:
                            config_args["response_mime_type"] = "application/json"

                        config = types.GenerateContentConfig(**config_args)
                        g_client = genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": max(1, int(remaining() * 1000))})
                        g_resp = g_client.models.generate_content(
                            model=gem_model,
                            contents=contents,
                            config=config
                        )
                        raw_text = (g_resp.text or "").strip()

                        if json_mode:
                            ok, parsed, err = _clean_and_heal_json(raw_text)
                            if not ok:
                                return LLMResult(
                                    success=False,
                                    text=raw_text,
                                    provider_used=f"gemini/{gem_model}",
                                    error=err
                                )
                            logger.info(f"Served by Gemini model: {gem_model} (JSON)")
                            return LLMResult(
                                success=True,
                                text=raw_text,
                                parsed_json=parsed,
                                provider_used=f"gemini/{gem_model}"
                            )

                        logger.info(f"Served by Gemini model: {gem_model}")
                        return LLMResult(
                            success=True,
                            text=raw_text,
                            provider_used=f"gemini/{gem_model}"
                        )

                    except TimeoutError as timeout_err:
                        logger.warning(f"Gemini {gem_model} deadline exceeded: {timeout_err}")
                        return LLMResult(
                            success=False,
                            text="",
                            provider_used=f"gemini/{gem_model}",
                            error="DEADLINE_EXCEEDED"
                        )
                    except Exception as err:
                        err_str = str(err)
                        if "deadline exhausted" in err_str.lower():
                            return LLMResult(
                                success=False,
                                text="",
                                provider_used=f"gemini/{gem_model}",
                                error="DEADLINE_EXCEEDED"
                            )
                        if _is_transient_error(err_str) and attempt < (MAX_RETRIES_PER_MODEL - 1):
                            sleep_time = 0.5 * (attempt + 1)
                            logger.warning(f"Gemini {gem_model} transient error, retrying in {sleep_time}s...")
                            try:
                                rem = remaining()
                            except TimeoutError:
                                return LLMResult(success=False, text="", error="DEADLINE_EXCEEDED")
                            time.sleep(min(sleep_time, rem))
                            continue
                        logger.warning(f"Gemini {gem_model} failed: {err_str[:120]}. Failing to next model.")
                        break
        except TimeoutError:
            return LLMResult(success=False, text="", error="DEADLINE_EXCEEDED")
        except Exception as g_client_err:
            logger.warning(f"Gemini client init failed: {g_client_err}")

    # 3. Complete Provider Exhaustion
    logger.critical("All provider endpoints exhausted. Failing soft with SERVICE_UNAVAILABLE.")
    return LLMResult(
        success=False,
        text="",
        error="SERVICE_UNAVAILABLE"
    )
