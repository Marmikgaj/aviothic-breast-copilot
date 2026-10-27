"""Pydantic schemas for multi-turn conversational interaction.

Complies with Architecture §5 API contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.context.schemas import CitationReference, ConcordanceStatus


class ChatRequest(BaseModel):
    """Payload for conversational Q&A endpoint."""

    message: str = Field(..., min_length=1, max_length=4000, description="Clinician question or prompt")
    stream: bool = Field(default=False, description="Whether to stream response (v2)")
    max_citations: int = Field(default=3, ge=1, le=10, description="Maximum citations to return")


class ChatResponse(BaseModel):
    """Structured response for a conversation turn."""

    session_id: str = Field(..., description="Active session ID")
    turn_id: str = Field(..., description="Generated turn ID")
    response: str = Field(..., description="Grounded, safety-audited assistant answer")
    citations: list[CitationReference] = Field(default_factory=list, description="Grounding citations")
    concordance_status: ConcordanceStatus | None = Field(
        default=None, description="Radiologic-pathologic concordance evaluation if applicable"
    )
    is_safe: bool = Field(default=True, description="True if answer satisfied all safety constraints")
    latency_ms: float = Field(..., description="Inference and retrieval latency in milliseconds")
