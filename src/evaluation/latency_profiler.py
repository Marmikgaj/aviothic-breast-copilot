"""Latency benchmark profiler for ingestion, extraction, and chat turn pipelines.

Validates against PRD §6 targets:
- Report ingestion + extraction latency <= 30s p95
- Conversational turn latency <= 5s p95
"""

from __future__ import annotations

import math
import statistics
import time

from src.context.schemas import ProcessedReport, ReportModality
from src.context.session_manager import SessionManager
from src.conversation.engine import ConversationEngine
from src.core.logging import get_logger
from src.evaluation.schemas import LatencyBenchmarkResult
from src.extraction.engine import extract_entities
from src.ingestion.report_classifier import detect_report_type
from src.ingestion.text_cleaner import clean_text

logger = get_logger(__name__)


def compute_percentiles(
    samples_ms: list[float], operation_name: str, threshold_p95_ms: float
) -> LatencyBenchmarkResult:
    """Compute distribution statistics and determine pass/fail against threshold."""
    if not samples_ms:
        return LatencyBenchmarkResult(
            operation_name=operation_name,
            sample_count=0,
            p50_ms=0.0,
            p90_ms=0.0,
            p95_ms=0.0,
            max_ms=0.0,
            mean_ms=0.0,
            threshold_p95_ms=threshold_p95_ms,
            passed_target=True,
        )

    sorted_s = sorted(samples_ms)
    n = len(sorted_s)

    p50_idx = max(0, min(n - 1, math.ceil(0.50 * n) - 1))
    p90_idx = max(0, min(n - 1, math.ceil(0.90 * n) - 1))
    p95_idx = max(0, min(n - 1, math.ceil(0.95 * n) - 1))

    p50 = round(sorted_s[p50_idx], 2)
    p90 = round(sorted_s[p90_idx], 2)
    p95 = round(sorted_s[p95_idx], 2)
    max_val = round(sorted_s[-1], 2)
    mean_val = round(statistics.mean(sorted_s), 2)
    passed = p95 <= threshold_p95_ms

    return LatencyBenchmarkResult(
        operation_name=operation_name,
        sample_count=n,
        p50_ms=p50,
        p90_ms=p90,
        p95_ms=p95,
        max_ms=max_val,
        mean_ms=mean_val,
        threshold_p95_ms=threshold_p95_ms,
        passed_target=passed,
    )


class LatencyProfiler:
    """Profiles end-to-end execution latencies across system pipelines."""

    def profile_ingestion_extraction(
        self,
        iterations: int = 15,
        sample_text: str | None = None,
    ) -> LatencyBenchmarkResult:
        """Profile text cleaning, modality classification, and entity extraction pipeline.

        Target: p95 <= 30,000 ms (30s) per PRD §6.
        """
        text = sample_text or (
            "DIAGNOSTIC MAMMOGRAM\n"
            "Right breast mass at 10 o'clock position measuring 18 mm. "
            "BI-RADS Category 4C: High suspicion for malignancy. Core biopsy recommended.\n"
            "HISTOLOGY: Invasive ductal carcinoma pT1c. ER positive 95%, PR positive 80%, HER2 negative 1+."
        )

        samples: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            cleaned = clean_text(text)
            _ = detect_report_type(cleaned)
            _ = extract_entities(cleaned)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            samples.append(elapsed_ms)

        result = compute_percentiles(samples, "Report Ingestion & Extraction", threshold_p95_ms=30000.0)
        logger.info(
            "Ingestion latency benchmark complete",
            p50_ms=result.p50_ms,
            p95_ms=result.p95_ms,
            passed=result.passed_target,
        )
        return result

    def profile_chat_turn(
        self,
        iterations: int = 15,
        query: str = "Explain the clinical significance of BI-RADS Category 4C.",
    ) -> LatencyBenchmarkResult:
        """Profile conversational turn latency including RAG retrieval, prompt assembly, and guardrails.

        Target: p95 <= 5,000 ms (5s) per PRD §6.
        """
        session_mgr = SessionManager()
        engine = ConversationEngine(session_manager=session_mgr)
        session = session_mgr.create_session(session_id="profile_chat_session")
        session_mgr.add_report(
            session.session_id,
            ProcessedReport(
                report_id="rep_prof_01",
                modality=ReportModality.MAMMOGRAPHY,
                date_str="2026-03-10",
                text="Mammogram: 18 mm right breast mass. BI-RADS Category 4C.",
            ),
        )

        samples: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            _ = engine.chat(session_id=session.session_id, message=query)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            samples.append(elapsed_ms)

        result = compute_percentiles(samples, "Conversational Turn", threshold_p95_ms=5000.0)
        logger.info(
            "Chat turn latency benchmark complete",
            p50_ms=result.p50_ms,
            p95_ms=result.p95_ms,
            passed=result.passed_target,
        )
        return result
