from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.repositories import ExtractionRepository
from core.extraction import extract_structured_data, validate_image_upload
from config import MAX_UPLOAD_SIZE_MB

router = APIRouter(prefix="/api", tags=["Structured Extraction"])


class DefaultExtractSchema(BaseModel):
    entity_name: str = Field(..., description="Identified entity, title, or document subject")
    category: str = Field(..., description="Domain classification (e.g. Invoice, Medical, Policy, Tech)")
    key_points: List[str] = Field(default_factory=list, description="Extracted key bullet points or summary facts")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score between 0.0 and 1.0")


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=16000, description="Unstructured text to extract data from")


class ExtractResponse(BaseModel):
    status: str
    extracted: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    job_id: Optional[str] = None


@router.post("/extract", response_model=ExtractResponse)
async def extract_text_endpoint(
    req: ExtractRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Extracts strictly validated Pydantic JSON from unstructured text.
    On schema failure, executes exactly 1 correction retry with specific validation feedback.
    """
    req_id = getattr(request.state, "request_id", None)
    ext_repo = ExtractionRepository(db)

    job = None
    try:
        job = await ext_repo.create_job(input_type="text", schema_name="DefaultExtractSchema")
    except Exception:
        pass

    res = extract_structured_data(
        schema=DefaultExtractSchema,
        text=req.text,
        request_id=req_id
    )

    if res.success and res.validated:
        data = res.validated.model_dump()
        if job:
            try:
                await ext_repo.complete_job(job.id, data)
            except Exception:
                pass
        return ExtractResponse(
            status="success",
            extracted=data,
            job_id=job.id if job else None
        )

    if job:
        try:
            await ext_repo.fail_job(job.id, res.error or "Extraction failed")
        except Exception:
            pass

    return ExtractResponse(
        status="failed",
        error=res.error or "Extraction failed to conform to required schema.",
        job_id=job.id if job else None
    )


@router.post("/extract/image", response_model=ExtractResponse)
async def extract_image_endpoint(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Multimodal structured extraction from uploaded image.
    Validates MIME type, file size, image headers, and enforces 1-attempt schema correction.
    """
    req_id = getattr(request.state, "request_id", None)
    
    # Read file bytes safely (enforce MAX_UPLOAD_SIZE_MB + 1 byte limit to reject large streams early)
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_bytes = await file.read(max_bytes + 1024)

    # File validation
    is_valid, err_msg = validate_image_upload(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
        max_size_mb=MAX_UPLOAD_SIZE_MB
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    ext_repo = ExtractionRepository(db)
    job = None
    try:
        job = await ext_repo.create_job(input_type="image", schema_name="DefaultExtractSchema")
    except Exception:
        pass

    mime_type = file.content_type or "image/png"
    res = extract_structured_data(
        schema=DefaultExtractSchema,
        image_bytes=file_bytes,
        mime_type=mime_type,
        request_id=req_id
    )

    if res.success and res.validated:
        data = res.validated.model_dump()
        if job:
            try:
                await ext_repo.complete_job(job.id, data)
            except Exception:
                pass
        return ExtractResponse(
            status="success",
            extracted=data,
            job_id=job.id if job else None
        )

    if job:
        try:
            await ext_repo.fail_job(job.id, res.error or "Multimodal extraction failed")
        except Exception:
            pass

    return ExtractResponse(
        status="failed",
        error=res.error or "Multimodal extraction failed to conform to schema.",
        job_id=job.id if job else None
    )
