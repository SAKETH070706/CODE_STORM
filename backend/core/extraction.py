import json
from typing import Type, TypeVar, Optional, Tuple
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass

from core.llm_client import call_llm
from config import MAX_UPLOAD_SIZE_MB, logger

T = TypeVar("T", bound=BaseModel)

ALLOWED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp"
}


@dataclass
class ExtractionResult:
    validated: Optional[BaseModel]
    raw_text: str
    success: bool
    error: Optional[str] = None


def validate_image_upload(
    file_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    max_size_mb: int = MAX_UPLOAD_SIZE_MB
) -> Tuple[bool, str]:
    """
    Validates uploaded image file bytes, size limit, and MIME type to prevent
    arbitrary file execution, oversized payloads, or path traversal attacks.
    """
    if not file_bytes or len(file_bytes) == 0:
        return False, "File is empty."

    max_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        return False, f"File size ({len(file_bytes)/(1024*1024):.2f}MB) exceeds limit of {max_size_mb}MB."

    # Validate filename if provided
    if filename:
        clean_name = filename.strip()
        if ".." in clean_name or "/" in clean_name or "\\" in clean_name:
            return False, "Dangerous filename or path traversal detected."

    # Validate MIME type
    norm_mime = (content_type or "").lower().strip()
    if norm_mime not in ALLOWED_MIME_TYPES:
        return False, f"Unsupported MIME type '{content_type}'. Allowed types: {', '.join(ALLOWED_MIME_TYPES.keys())}."

    # Magic byte header check for PNG, JPEG, WEBP
    if norm_mime in ("image/jpeg", "image/jpg"):
        if not file_bytes.startswith(b"\xff\xd8"):
            return False, "Malformed JPEG image header."
    elif norm_mime == "image/png":
        if not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Malformed PNG image header."
    elif norm_mime == "image/webp":
        if not (file_bytes.startswith(b"RIFF") and b"WEBP" in file_bytes[:16]):
            return False, "Malformed WEBP image header."

    return True, ""


def extract_structured_data(
    schema: Type[T],
    text: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
    custom_system_prompt: Optional[str] = None,
    request_id: Optional[str] = None
) -> ExtractionResult:
    """
    Extracts structured Pydantic data from text or image with exactly 1 feedback-driven correction retry.
    NEVER uses eval() or infinite loops.
    """
    schema_json_desc = json.dumps(schema.model_json_schema(), indent=2)
    default_system = (
        "You are an expert structured data extraction engine. "
        "Extract information strictly conforming to the following JSON schema:\n"
        f"{schema_json_desc}\n\n"
        "Return ONLY a valid JSON object matching this schema. Do not enclose in explanations."
    )
    system_prompt = custom_system_prompt or default_system
    user_prompt = text or "Extract the required structured fields from the attached image strictly conforming to the schema."

    # Attempt 1
    res1 = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_mode=True,
        image_bytes=image_bytes,
        mime_type=mime_type,
        request_id=request_id
    )

    if not res1.success or not res1.parsed_json:
        return ExtractionResult(
            validated=None,
            raw_text=res1.text,
            success=False,
            error=res1.error or "LLM failed to return structured JSON."
        )

    # Validate against Pydantic schema
    try:
        validated_obj = schema.model_validate(res1.parsed_json)
        return ExtractionResult(
            validated=validated_obj,
            raw_text=res1.text,
            success=True
        )
    except ValidationError as val_err1:
        last_val_err = str(val_err1)
        logger.warning(f"[{request_id or 'anon'}] Schema validation failed on attempt 1: {last_val_err[:120]}. Retrying once with error feedback...")

    # Attempt 2 (Correction Retry)
    retry_prompt = (
        f"{user_prompt}\n\n"
        "CRITICAL ERROR: Your previous JSON output failed validation against the schema.\n"
        f"Validation Error:\n{last_val_err}\n\n"
        "Fix the formatting, correct the field names/types, and output the valid JSON object strictly."
    )

    res2 = call_llm(
        system_prompt=system_prompt,
        user_prompt=retry_prompt,
        json_mode=True,
        image_bytes=image_bytes,
        mime_type=mime_type,
        request_id=request_id
    )

    if res2.success and res2.parsed_json:
        try:
            validated_obj = schema.model_validate(res2.parsed_json)
            return ExtractionResult(
                validated=validated_obj,
                raw_text=res2.text,
                success=True
            )
        except ValidationError as val_err2:
            logger.warning(f"[{request_id or 'anon'}] Schema validation failed on retry: {val_err2}")
            return ExtractionResult(
                validated=None,
                raw_text=res2.text,
                success=False,
                error=f"Schema validation error: {str(val_err2)}"
            )

    return ExtractionResult(
        validated=None,
        raw_text=res2.text or res1.text,
        success=False,
        error="Extraction retry failed to produce valid schema-compliant JSON."
    )
