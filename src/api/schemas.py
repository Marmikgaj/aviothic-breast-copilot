"""Pydantic v2 request/response schemas for the API layer.

All API payloads are validated through these models (Rules.md §5).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ============================================================================
# Shared / Nested Models
# ============================================================================


class ErrorDetail(BaseModel):
    """Structured error response body."""

    code: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable error description.")
    correlation_id: str = Field(..., description="Request correlation ID for traceability.")


class ErrorResponse(BaseModel):
    """Wrapper for structured error responses."""

    error: ErrorDetail


class ReportConfidence(BaseModel):
    """Confidence scores for each extraction step."""

    text_extraction: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in the text extraction quality."
    )
    report_type_detection: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in the detected report type."
    )
    report_date_detection: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in the detected report date."
    )


# ============================================================================
# Report Result
# ============================================================================


class ReportResult(BaseModel):
    """Structured output from report processing."""

    report_id: str = Field(..., description="Unique identifier for this report.")
    report_type: str | None = Field(
        None,
        description="Detected report modality: mammography, ultrasound, mri, pet_ct, pathology, discharge, or unknown.",
    )
    report_date: str | None = Field(None, description="Detected report date in ISO 8601 format.")
    raw_text: str = Field(..., description="Full cleaned text extracted from the report.")
    page_count: int = Field(..., ge=0, description="Number of pages in the uploaded document.")
    text_length: int = Field(..., ge=0, description="Character count of the cleaned text.")
    processing_time_ms: float = Field(..., ge=0, description="Total processing time in milliseconds.")
    confidence: ReportConfidence = Field(..., description="Confidence scores for each extraction step.")
    is_scanned_likely: bool = Field(
        False,
        description="True if the document appears to be scanned/image-based and may need OCR (not yet supported).",
    )


# ============================================================================
# Upload Endpoint
# ============================================================================


class UploadResponse(BaseModel):
    """Response returned immediately after a report upload is accepted."""

    report_id: str = Field(..., description="Unique identifier assigned to this report.")
    status: Literal["processing", "completed", "failed"] = Field(
        ..., description="Current processing status."
    )
    message: str = Field(..., description="Human-readable status message.")


# ============================================================================
# Status Polling Endpoint
# ============================================================================


class ReportStatusResponse(BaseModel):
    """Response for the report status polling endpoint."""

    report_id: str = Field(..., description="Unique identifier for this report.")
    status: Literal["processing", "completed", "failed"] = Field(
        ..., description="Current processing status."
    )
    result: ReportResult | None = Field(None, description="Processing result (present when status is 'completed').")
    error: ErrorDetail | None = Field(None, description="Error details (present when status is 'failed').")


# ============================================================================
# Health Endpoint
# ============================================================================


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""

    status: str = Field(..., description="Service health status.")
    version: str = Field(..., description="Application version.")
    timestamp: str = Field(..., description="Current server timestamp in ISO 8601.")
    environment: str = Field(..., description="Runtime environment (development/staging/production).")
