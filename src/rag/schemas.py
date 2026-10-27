"""Domain schemas and models for the Oncology RAG engine.

Provides structured models for guidelines, literature abstracts, retrieved passages,
and citation metadata per ADR-005 and PRD §4.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GuidelineSource(StrEnum):
    """Clinical authoritative source for oncology literature."""

    NCCN = "NCCN"
    ASCO_CAP = "ASCO_CAP"
    AJCC = "AJCC"
    PUBMED = "PUBMED"
    ESMO = "ESMO"


class GuidelineDocument(BaseModel):
    """Authoritative oncology guideline or PubMed reference document."""

    id: str = Field(..., description="Unique document ID (e.g., 'nccn_birads_mgmt_2024').")
    title: str = Field(..., description="Full clinical title.")
    source: GuidelineSource = Field(..., description="Source authority.")
    authors: str = Field("", description="Author list or committee name.")
    year: int | None = Field(None, description="Publication or revision year.")
    text: str = Field(..., description="Guideline passage, protocol text, or abstract content.")
    doi_or_pmid: str | None = Field(None, description="PubMed ID or DOI for verification.")
    citation_label: str = Field(..., description="Short inline citation label (e.g., '[NCCN 2024]').")
    url: str | None = Field(None, description="Direct URL to open-access publication or summary.")
    keywords: list[str] = Field(default_factory=list, description="Clinical keywords.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extended document attributes.")


class RetrievedPassage(BaseModel):
    """Single passage retrieved from the vector index."""

    id: str = Field(..., description="Passage ID in the vector collection.")
    document_id: str = Field(..., description="Source GuidelineDocument ID.")
    text: str = Field(..., description="Retrieved passage text.")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (normalized 0.0 to 1.0).")
    citation_label: str = Field(..., description="Inline citation label.")
    source: GuidelineSource = Field(..., description="Source organization.")
    title: str = Field(..., description="Document title.")
    doi_or_pmid: str | None = Field(None, description="Auditable PMID or DOI.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Passage metadata.")


class RetrievalQuery(BaseModel):
    """Query specification for clinical literature retrieval."""

    query: str = Field(..., min_length=2, description="Clinical query or finding description.")
    top_k: int = Field(3, ge=1, le=20, description="Maximum number of passages to retrieve.")
    sources: list[GuidelineSource] | None = Field(None, description="Optional source filter.")
    min_similarity: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity cutoff.")


class RetrievalResult(BaseModel):
    """Aggregated retrieval results with citation provenance."""

    query: str = Field(..., description="Original search query.")
    passages: list[RetrievedPassage] = Field(default_factory=list, description="Top-k matching passages.")
    formatted_citations: str = Field("", description="Numbered reference list for clinical review.")
    latency_ms: float = Field(..., ge=0.0, description="Vector retrieval latency in milliseconds.")

    def to_context_string(self) -> str:
        """Format retrieved passages into a structured prompt context block.

        Returns:
            Grounded context string with inline citation markers.
        """
        if not self.passages:
            return "No relevant clinical guidelines found for this query."

        blocks: list[str] = []
        for i, p in enumerate(self.passages, start=1):
            ref = f"[{i}] {p.citation_label} ({p.title})"
            blocks.append(f"Passage {ref}:\n{p.text}")
        return "\n\n".join(blocks)
