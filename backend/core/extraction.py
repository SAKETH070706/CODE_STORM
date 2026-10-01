import json
from typing import Type, TypeVar, Optional, Union, Tuple
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass

from core.llm_client import call_llm
from config import logger

T = TypeVar("T", bound=BaseModel)

@dataclass
class ExtractionResult:
    validated: Optional[BaseModel]
    raw_text: str
    success: bool
    error: Optional[str] = None

def extract_structured_data(
    schema: Type[T],
    text: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/png",
    custom_system_prompt: Optional[str] = None
) -> ExtractionResult:
    """Extracts structured data with 1-attempt validation feedback retry."""
    schema_json_desc = json.dumps(schema.model_json_schema(), indent=2)
    default_system = (
        "You are a strict data extraction engine. Extract information matching the following JSON schema:\n"
        f"{schema_json_desc}\n\n"
        "Output ONLY valid JSON matching this schema."
    )
    system_prompt = custom_system_prompt or default_system
    user_prompt = text or "Extract the required structured fields from the attached image strictly according to the schema."

    res1 = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_mode=True,
        image_bytes=image_bytes,
        mime_type=mime_type
    )

    if not res1.success or not res1.parsed_json:
        return ExtractionResult(
            validated=None,
            raw_text=res1.text,
            success=False,
            error=res1.error or "LLM failed to return structured JSON."
        )

    last_val_err = ""
    try:
        validated_obj = schema.model_validate(res1.parsed_json)
        return ExtractionResult(
            validated=validated_obj,
            raw_text=res1.text,
            success=True
        )
    except ValidationError as val_err1:
        last_val_err = str(val_err1)
        logger.warning(f"Schema validation failed on attempt 1: {last_val_err}. Retrying once with error feedback...")

    retry_prompt = (
        f"{user_prompt}\n\n"
        "ATTENTION: Your previous JSON output was invalid according to the schema.\n"
        f"Validation Error: {last_val_err}\n"
        "Please fix the fields and output the corrected JSON object strictly."
    )

    res2 = call_llm(
        system_prompt=system_prompt,
        user_prompt=retry_prompt,
        json_mode=True,
        image_bytes=image_bytes,
        mime_type=mime_type
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
            logger.warning(f"Schema validation failed on attempt 2: {val_err2}. Returning raw text fallback.")
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


def validate_image_upload(
    file_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    max_size_mb: int = 10
) -> Tuple[bool, str]:
    """
    Validates uploaded image file:
    1. Enforces size limit.
    2. Validates filename against path traversal.
    3. Validates MIME type against allowed list.
    4. Validates binary magic byte signatures (PNG: \x89PNG, JPEG: \xff\xd8, WebP: RIFF...WEBP).
    """
    if not file_bytes:
        return False, "Uploaded file is empty."

    max_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        return False, f"File size exceeds maximum allowed size of {max_size_mb} MB."

    if filename:
        if ".." in filename or "/" in filename or "\\" in filename:
            return False, "Invalid filename: path traversal characters detected."

    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if content_type and content_type.lower() not in allowed_types:
        return False, f"Unsupported content type '{content_type}'. Allowed types: image/png, image/jpeg, image/webp."

    # Validate binary magic headers
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return True, ""
    if file_bytes.startswith(b"\xff\xd8"):
        return True, ""
    if file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
        return True, ""

    return False, "File content does not match a valid PNG, JPEG, or WebP image signature."

