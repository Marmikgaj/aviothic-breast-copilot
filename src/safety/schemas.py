"""Pydantic schemas for the safety guardrail and citation enforcement layer.

Complies with Rules.md §8 (NEVER diagnose or assert definitive malignancy)
and Architecture §2 (Auditability & Safety).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SafetyCheckResult(BaseModel):
    """Result of safety, non-diagnostic, and citation audit on an assistant response."""

    is_safe: bool = Field(..., description="True if response passes all clinical safety constraints")
    has_diagnostic_leakage: bool = Field(
        default=False, description="True if prohibited definitive diagnostic assertions were detected"
    )
    has_disclaimer: bool = Field(default=True, description="True if mandatory assistive disclaimer is present")
    has_citations: bool = Field(
        default=True, description="True if required citations are present when clinical claims are made"
    )
    is_off_context: bool = Field(
        default=False, description="True if query is out of domain or unrelated to clinical reports"
    )
    violations: list[str] = Field(default_factory=list, description="Specific safety violations detected")
    sanitized_response: str = Field(..., description="Post-guardrail sanitized and audited response text")
