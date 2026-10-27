"""Pydantic v2 request/response schemas for the API layer.

All API payloads are validated through these models (Rules.md §5).
"""

from __future__ import annotations

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
# Clinical Entity Extraction Models (Phase 3)
# ============================================================================


class SourceSpan(BaseModel):
    """Source text character offsets for 100% auditable clinical claims (Rules.md §3)."""

    start_char: int = Field(..., ge=0, description="Start character offset in raw_text.")
    end_char: int = Field(..., ge=0, description="End character offset in raw_text.")
    snippet: str = Field(..., description="Exact string snippet extracted from the source text.")


class BiradsEntity(BaseModel):
    """Extracted BI-RADS assessment entity."""

    category: str = Field(..., description="BI-RADS category: 0, 1, 2, 3, 4, 4A, 4B, 4C, 5, or 6.")
    descriptor: str | None = Field(
        None, description="Category descriptor narrative (e.g., 'Low Suspicion for Malignancy')."
    )
    side: Literal["left", "right", "bilateral", "unspecified"] = Field(
        "unspecified", description="Breast side associated with assessment."
    )
    span: SourceSpan = Field(..., description="Source text character span.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score.")


class TnmEntity(BaseModel):
    """Extracted TNM staging entity."""

    raw_stage: str = Field(..., description="Full raw TNM stage string (e.g., 'pT1c N0 M0').")
    t_stage: str | None = Field(None, description="Primary tumor stage (e.g., 'pTis', 'pT1c', 'T2').")
    n_stage: str | None = Field(None, description="Regional lymph node stage (e.g., 'N0', 'pN1a').")
    m_stage: str | None = Field(None, description="Distant metastasis stage (e.g., 'M0', 'pM1').")
    is_pathological: bool = Field(True, description="True if pathological (pTNM), False if clinical (cTNM).")
    span: SourceSpan = Field(..., description="Source text character span.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score.")


class BiomarkerEntity(BaseModel):
    """Extracted immunohistochemistry (IHC) / FISH biomarker entity."""

    name: Literal["ER", "PR", "HER2", "Ki-67"] = Field(..., description="Biomarker target name.")
    status: Literal["positive", "negative", "equivocal", "unknown"] = Field(
        ..., description="Qualitative biomarker status."
    )
    percentage: float | None = Field(
        None, ge=0.0, le=100.0, description="Quantitative percentage (e.g., 90% for ER/PR/Ki-67)."
    )
    intensity: Literal["strong", "moderate", "weak", "none", "unknown"] = Field(
        "unknown", description="Staining intensity narrative."
    )
    ihc_score: str | None = Field(None, description="HER2 IHC score (e.g., '0', '1+', '2+', '3+').")
    fish_status: Literal["amplified", "non-amplified", "equivocal", "not_performed"] = Field(
        "not_performed", description="HER2 FISH gene amplification status."
    )
    span: SourceSpan = Field(..., description="Source text character span.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score.")


class TumorDimensionEntity(BaseModel):
    """Extracted tumor dimension, size, and anatomical location entity."""

    primary_size_mm: float | None = Field(None, ge=0.0, description="Largest primary tumor dimension in millimeters.")
    dimensions_mm: list[float] = Field(default_factory=list, description="All measured dimensions in mm (up to 3D).")
    location_quadrant: str | None = Field(None, description="Quadrant location (e.g., 'upper outer quadrant').")
    clock_position: str | None = Field(None, description="Clock position (e.g., '10 o'clock').")
    span: SourceSpan = Field(..., description="Source text character span.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score.")


class LymphNodeEntity(BaseModel):
    """Extracted axillary / sentinel lymph node status entity."""

    nodes_examined: int | None = Field(None, ge=0, description="Total number of lymph nodes examined.")
    nodes_positive: int | None = Field(None, ge=0, description="Number of lymph nodes positive for metastasis.")
    sentinel_status: bool | None = Field(
        None, description="True if sentinel lymph node biopsy, False if axillary dissection."
    )
    extranodal_extension: bool | None = Field(None, description="Presence of extranodal extension.")
    span: SourceSpan = Field(..., description="Source text character span.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score.")


class ExtractedEntities(BaseModel):
    """Structured container holding all extracted clinical entities for a report."""

    birads: list[BiradsEntity] = Field(default_factory=list, description="Extracted BI-RADS assessment entities.")
    tnm_staging: list[TnmEntity] = Field(default_factory=list, description="Extracted TNM staging entities.")
    biomarkers: list[BiomarkerEntity] = Field(default_factory=list, description="Extracted biomarker entities.")
    tumor_dimensions: list[TumorDimensionEntity] = Field(
        default_factory=list, description="Extracted tumor dimension entities."
    )
    lymph_nodes: list[LymphNodeEntity] = Field(default_factory=list, description="Extracted lymph node entities.")


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
        description="True if the document appears to be scanned/image-based.",
    )
    ocr_warning: str | None = Field(
        None,
        description="Warning message when OCR confidence is low or Tesseract is unavailable.",
    )
    entities: ExtractedEntities | None = Field(
        None,
        description="Extracted clinical entities (BI-RADS, TNM, biomarkers, tumor dimensions, lymph nodes).",
    )


# ============================================================================
# Upload Endpoint
# ============================================================================


class UploadResponse(BaseModel):
    """Response returned immediately after a report upload is accepted."""

    report_id: str = Field(..., description="Unique identifier assigned to this report.")
    status: Literal["processing", "completed", "failed"] = Field(..., description="Current processing status.")
    message: str = Field(..., description="Human-readable status message.")


# ============================================================================
# Status Polling Endpoint
# ============================================================================


class ReportStatusResponse(BaseModel):
    """Response for the report status polling endpoint."""

    report_id: str = Field(..., description="Unique identifier for this report.")
    status: Literal["processing", "completed", "failed"] = Field(..., description="Current processing status.")
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
