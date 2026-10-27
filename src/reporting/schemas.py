"""Pydantic schemas for clinical and patient-friendly report summaries and JSON export.

Complies with PRD §3, §4 and Architecture §4 & §5.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.context.schemas import ConcordanceStatus, MultiReportTimelineEntry


class SummaryRequest(BaseModel):
    """Request options for generating session clinical summaries."""

    audience: Literal["both", "clinician", "patient"] = Field(
        default="both", description="Target audience for generated summaries"
    )
    include_timeline: bool = Field(default=True, description="Whether to include chronological timeline")


class SummaryResponse(BaseModel):
    """Combined clinician and patient-friendly summaries."""

    session_id: str = Field(..., description="Active session ID")
    clinician_summary: str = Field(..., description="Dense technical summary for clinical notes and EHR pasting")
    patient_summary: str = Field(
        ...,
        description="Plain-language explanation for clinician review before sharing with the patient",
    )
    concordance_status: ConcordanceStatus = Field(
        default=ConcordanceStatus.NOT_APPLICABLE,
        description="Radiologic-pathologic concordance evaluation",
    )
    timeline: list[MultiReportTimelineEntry] = Field(
        default_factory=list, description="Chronological diagnostic events"
    )
    disclaimer: str = Field(..., description="Mandatory non-diagnostic assistive disclaimer")


class SessionExport(BaseModel):
    """Complete structured JSON export for a patient session."""

    session_id: str = Field(..., description="Unique session identifier")
    created_at: str = Field(..., description="Session creation timestamp (ISO 8601)")
    updated_at: str = Field(..., description="Session last updated timestamp (ISO 8601)")
    total_reports: int = Field(..., description="Number of reports in session")
    modalities_present: list[str] = Field(default_factory=list, description="All modalities uploaded")
    concordance: ConcordanceStatus = Field(default=ConcordanceStatus.NOT_APPLICABLE)
    concordance_notes: list[str] = Field(default_factory=list)
    timeline: list[MultiReportTimelineEntry] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list, description="Audited reports with entity spans")
    conversation_history: list[dict[str, Any]] = Field(default_factory=list, description="Full multi-turn history")
    metadata: dict[str, Any] = Field(default_factory=dict)
