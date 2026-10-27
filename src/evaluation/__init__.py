"""Phase 8 System Evaluation and Benchmark Suite."""

from src.evaluation.extraction_evaluator import ExtractionEvaluator
from src.evaluation.gold_dataset import GOLD_BENCHMARK_CASES, GoldBenchmarkCase
from src.evaluation.hallucination_evaluator import HallucinationEvaluator
from src.evaluation.latency_profiler import LatencyProfiler
from src.evaluation.runner import run_full_system_evaluation
from src.evaluation.schemas import (
    EntityMetric,
    ExtractionEvaluationResult,
    FullSystemEvaluationReport,
    HallucinationEvaluationResult,
    LatencyBenchmarkResult,
)

__all__ = [
    "EntityMetric",
    "ExtractionEvaluationResult",
    "ExtractionEvaluator",
    "FullSystemEvaluationReport",
    "GOLD_BENCHMARK_CASES",
    "GoldBenchmarkCase",
    "HallucinationEvaluationResult",
    "HallucinationEvaluator",
    "LatencyBenchmarkResult",
    "LatencyProfiler",
    "run_full_system_evaluation",
]
