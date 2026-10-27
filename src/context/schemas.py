"""Pydantic schemas for session-scoped patient context, multi-report records, and conversation history.

Complies with Architecture §4, PRD §7 (ephemeral session scoping), and ADR-002.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.api.schemas import ExtractedEntities
from src.rag.schemas import GuidelineSource


class ConversationRole(StrEnum):
    """Role of a participant in a conversation turn."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CitationSourceType(StrEnum):
    """Source classification for a clinical citation."""

    REPORT = "report"
    GUIDELINE = "guideline"
    PUBMED = "pubmed"


class ReportModality(StrEnum):
    """Clinical report imaging or diagnostic modality."""

    MAMMOGRAPHY = "mammography"
    PATHOLOGY = "pathology"
    ULTRASOUND = "ultrasound"
    MRI = "mri"
    PET_CT = "pet_ct"
    DISCHARGE_SUMMARY = "discharge_summary"
    UNKNOWN = "unknown"


class CitationReference(BaseModel):
    """Citation linking a factual claim to a verified source."""

    source_type: CitationSourceType = Field(..., description="Origin category of citation")
    source_id: str = Field(..., description="Report ID or guideline/PubMed identifier")
    text_snippet: str = Field(..., description="Concise text snippet or evidence quote")
    retrieval_score: float | None = Field(default=None, description="Similarity or relevance score")
    guideline_source: GuidelineSource | None = Field(
        default=None, description="Clinical issuing body (e.g., NCCN, ASCO)"
    )


class ConversationTurn(BaseModel):
    """A single turn within a multi-turn chat session."""

    turn_id: str = Field(default_factory=lambda: f"turn_{uuid.uuid4().hex[:12]}")
    role: ConversationRole = Field(..., description="Role of the message author")
    content: str = Field(..., description="Message text")
    citations: list[CitationReference] = Field(default_factory=list, description="Grounding citations")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProcessedReport(BaseModel):
    """An ingested and structured clinical report associated with a patient session."""

    report_id: str = Field(..., description="Unique report identifier")
    modality: ReportModality = Field(default=ReportModality.UNKNOWN, description="Clinical report modality")
    date_str: str | None = Field(default=None, description="Detected clinical date of examination (YYYY-MM-DD)")
    text: str = Field(..., description="Normalized and cleaned report text")
    entities: ExtractedEntities = Field(
        default_factory=ExtractedEntities, description="Structured extracted clinical entities"
    )
    ocr_confidence: float | None = Field(default=None, description="OCR confidence if scanned PDF")
    upload_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def chronological_date(self) -> str:
        """String representation of report date for chronological sorting."""
        if self.date_str:
            return self.date_str
        return self.upload_timestamp.strftime("%Y-%m-%d")


class ConcordanceStatus(StrEnum):
    """Radiologic-pathologic concordance evaluation."""

    CONCORDANT = "concordant"
    DISCORDANT = "discordant"
    INDETERMINATE = "indeterminate"
    NOT_APPLICABLE = "not_applicable"


class MultiReportTimelineEntry(BaseModel):
    """Timeline entry representing an event in the patient's diagnostic trajectory."""

    report_id: str
    date_str: str
    modality: ReportModality
    key_findings: list[str] = Field(default_factory=list)
    birads_category: str | None = None
    tnm_stage: str | None = None
    biomarkers: dict[str, str] = Field(default_factory=dict)


class MultiReportSummary(BaseModel):
    """Unified multi-report synthesis across a single patient session."""

    session_id: str
    total_reports: int
    modalities_present: list[ReportModality]
    timeline: list[MultiReportTimelineEntry]
    concordance: ConcordanceStatus = ConcordanceStatus.NOT_APPLICABLE
    concordance_notes: list[str] = Field(default_factory=list)
    aggregated_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)


class PatientContext(BaseModel):
    """Session-scoped container holding all reports and conversational memory.

    Ephemeral: Lives exclusively during the patient session and is never persisted
    to external cross-patient databases per PRD §7.
    """

    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    reports: list[ProcessedReport] = Field(default_factory=list, description="Reports uploaded during this session")
    history: list[ConversationTurn] = Field(default_factory=list, description="Multi-turn conversation history")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Session-scoped ephemeral metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(UTC)

    def get_report(self, report_id: str) -> ProcessedReport | None:
        """Find a report in this session by ID."""
        for report in self.reports:
            if report.report_id == report_id:
                return report
        return None


class ContextBudget(BaseModel):
    """Token budget configuration for prompt context window assembly."""

    max_tokens: int = Field(default=4096, description="Total maximum model context window")
    reserved_completion_tokens: int = Field(default=1024, description="Tokens reserved for LLM response generation")
    system_prompt_tokens: int = Field(
        default=512, description="Tokens reserved for safety rules and system instructions"
    )
    safety_margin: int = Field(default=128, description="Token buffer for markup and framing")

    @property
    def available_context_tokens(self) -> int:
        """Tokens available for report text, history, and retrieved guidelines."""
        return max(
            256,
            self.max_tokens - self.reserved_completion_tokens - self.system_prompt_tokens - self.safety_margin,
        )
