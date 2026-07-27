"""Upload and report status endpoints.

``POST /api/v1/upload`` — accepts a PDF, validates it, kicks off async processing.
``GET /api/v1/reports/{report_id}/status`` — polls the processing result.

The async processing uses an in-memory dict as the job store for Phase 1.
This is an intentional simplification — acceptable per the single-node,
low-concurrency assumptions in PRD §7.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, UploadFile

from src.api.middleware import api_key_header
from src.api.schemas import (
    ErrorDetail,
    ReportResult,
    ReportStatusResponse,
    UploadResponse,
)
from src.core.config import get_settings
from src.core.exceptions import ReportNotFoundError
from src.core.logging import correlation_id_ctx, get_logger
from src.ingestion.pipeline import process_report
from src.ingestion.validator import validate_upload

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["reports"],
    dependencies=[Depends(api_key_header)],
)

# In-memory job store — Phase 1 simplification.
# Keys are report_id strings, values are ReportStatusResponse dicts.
_job_store: dict[str, dict[str, Any]] = {}


def get_job_store() -> dict[str, dict[str, Any]]:
    """Return the in-memory job store (for testing access)."""
    return _job_store


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=202,
    summary="Upload a report",
    description="Upload a breast imaging or pathology report (PDF). Returns a report ID for status polling.",
    responses={
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        422: {"description": "File validation error"},
    },
)
async def upload_report(file: UploadFile) -> UploadResponse:
    """Accept a PDF upload, validate it, and start async processing."""
    settings = get_settings()
    report_id = str(uuid.uuid4())

    logger.info(
        "Upload received",
        report_id=report_id,
        filename=file.filename,
        content_type=file.content_type,
    )

    # Validate the uploaded file (size, MIME type, magic bytes).
    validated_file = await validate_upload(file=file, settings=settings)

    # Initialize job status as processing.
    _job_store[report_id] = {
        "report_id": report_id,
        "status": "processing",
        "result": None,
        "error": None,
    }

    # Kick off async processing.
    asyncio.create_task(
        _run_processing(report_id=report_id, content=validated_file.content, filename=validated_file.filename)
    )

    return UploadResponse(
        report_id=report_id,
        status="processing",
        message="Report accepted. Poll /api/v1/reports/{report_id}/status for results.",
    )


async def _run_processing(*, report_id: str, content: bytes, filename: str) -> None:
    """Run the processing pipeline and update the job store on completion or failure."""
    start_time = time.monotonic()

    try:
        result = await process_report(report_id=report_id, content=content, filename=filename)
        elapsed_ms = (time.monotonic() - start_time) * 1000

        _job_store[report_id] = {
            "report_id": report_id,
            "status": "completed",
            "result": result.model_dump(),
            "error": None,
        }

        logger.info(
            "Report processing completed",
            report_id=report_id,
            processing_time_ms=round(elapsed_ms, 2),
            report_type=result.report_type,
        )

    except Exception as exc:
        correlation_id = correlation_id_ctx.get() or "unknown"
        logger.exception("Report processing failed", report_id=report_id)

        _job_store[report_id] = {
            "report_id": report_id,
            "status": "failed",
            "result": None,
            "error": {
                "code": "FILE_PROCESSING_ERROR",
                "message": f"Processing failed: {exc}",
                "correlation_id": correlation_id,
            },
        }


@router.get(
    "/reports/{report_id}/status",
    response_model=ReportStatusResponse,
    summary="Poll report status",
    description="Check the processing status of a previously uploaded report.",
    responses={
        404: {"description": "Report not found"},
    },
)
async def get_report_status(report_id: str) -> ReportStatusResponse:
    """Return the current processing status for a given report ID."""
    job = _job_store.get(report_id)

    if job is None:
        raise ReportNotFoundError(report_id=report_id)

    return ReportStatusResponse(
        report_id=job["report_id"],
        status=job["status"],
        result=ReportResult(**job["result"]) if job["result"] else None,
        error=ErrorDetail(**job["error"]) if job["error"] else None,
    )
