"""Pydantic schemas for Phase 8 benchmark evaluation, precision/recall, hallucination, and latency profiling.

Complies with PRD §6 Success Metrics and Phases §8.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class EntityMetric(BaseModel):
    """Precision, recall, and F1 score for a single clinical entity category."""

    true_positives: int = Field(default=0, ge=0)
    false_positives: int = Field(default=0, ge=0)
    false_negatives: int = Field(default=0, ge=0)
    precision: float = Field(default=0.0, ge=0.0, le=1.0)
    recall: float = Field(default=0.0, ge=0.0, le=1.0)
    f1_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ExtractionEvaluationResult(BaseModel):
    """Extraction benchmark evaluation report across all clinical entity categories."""

    entity_metrics: dict[str, EntityMetric] = Field(default_factory=dict)
    macro_precision: float = Field(..., ge=0.0, le=1.0)
    macro_recall: float = Field(..., ge=0.0, le=1.0)
    macro_f1: float = Field(..., ge=0.0, le=1.0)
    total_gold_entities: int = Field(..., ge=0)
    total_extracted_entities: int = Field(..., ge=0)
    passed_target: bool = Field(..., description="True if macro precision and recall >= 0.85 per PRD §6")


class HallucinationEvaluationResult(BaseModel):
    """Evaluation of hallucination rate, citation binding, and safety disclaimer adherence."""

    total_turns: int = Field(..., ge=0)
    compliant_turns: int = Field(..., ge=0)
    hallucination_count: int = Field(..., ge=0, description="Claims made without valid grounded citations")
    hallucination_rate: float = Field(..., ge=0.0, le=1.0, description="Target: < 0.05 per PRD §6")
    diagnostic_leakage_count: int = Field(..., ge=0, description="Definitive diagnostic assertions")
    diagnostic_leakage_rate: float = Field(..., ge=0.0, le=1.0, description="Target: < 0.05 per Rules.md §8")
    disclaimer_presence_rate: float = Field(..., ge=0.0, le=1.0, description="Target: >= 0.95 per PRD §4")
    passed_target: bool = Field(..., description="True if hallucination and leakage rates meet target thresholds")


class LatencyBenchmarkResult(BaseModel):
    """Latency distribution profiling for clinical pipelines."""

    operation_name: str
    sample_count: int = Field(..., ge=1)
    p50_ms: float = Field(..., ge=0.0)
    p90_ms: float = Field(..., ge=0.0)
    p95_ms: float = Field(..., ge=0.0)
    max_ms: float = Field(..., ge=0.0)
    mean_ms: float = Field(..., ge=0.0)
    threshold_p95_ms: float = Field(..., ge=0.0)
    passed_target: bool = Field(..., description="True if p95 latency is within threshold")


class FullSystemEvaluationReport(BaseModel):
    """Complete Phase 8 system verification report covering all PRD §6 criteria."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extraction_eval: ExtractionEvaluationResult
    hallucination_eval: HallucinationEvaluationResult
    ingestion_latency: LatencyBenchmarkResult
    chat_latency: LatencyBenchmarkResult
    overall_system_passed: bool = Field(..., description="True if all PRD §6 targets are satisfied")
    metadata: dict[str, Any] = Field(default_factory=dict)
