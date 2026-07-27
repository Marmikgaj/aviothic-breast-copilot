"""Report processing pipeline — orchestrates extraction, cleaning, classification, and dating.

This is the main entry point called by the upload router's async task.
"""

from __future__ import annotations

import time

from src.api.schemas import ReportConfidence, ReportResult
from src.core.exceptions import FileProcessingError
from src.core.logging import get_logger
from src.ingestion.date_extractor import detect_report_date
from src.ingestion.pdf_extractor import extract_text
from src.ingestion.report_classifier import detect_report_type
from src.ingestion.text_cleaner import clean_text

logger = get_logger(__name__)


async def process_report(*, report_id: str, content: bytes, filename: str) -> ReportResult:
    """Process an uploaded PDF through the full ingestion pipeline.

    Pipeline steps:
        1. PDF text extraction (PyMuPDF → pdfplumber fallback).
        2. Text cleaning and normalization.
        3. Report type classification (keyword-based).
        4. Report date detection (regex-based).
        5. Assemble structured result.

    Args:
        report_id: Unique identifier for this report.
        content: Raw bytes of the uploaded PDF.
        filename: Original filename of the upload.

    Returns:
        A ``ReportResult`` with all extracted metadata and the cleaned text.

    Raises:
        FileProcessingError: If a critical step in the pipeline fails.
    """
    start_time = time.monotonic()

    logger.info("Processing report", report_id=report_id, filename=filename)

    # --- Step 1: PDF text extraction ---
    try:
        extraction_result = extract_text(content)
    except Exception as exc:
        raise FileProcessingError(f"PDF text extraction failed: {exc}") from exc

    # Handle likely-scanned documents.
    if extraction_result.is_scanned_likely:
        logger.warning(
            "Document appears to be scanned — OCR not yet supported (Phase 2)",
            report_id=report_id,
        )

    # --- Step 2: Text cleaning ---
    try:
        cleaned_text = clean_text(extraction_result.raw_text)
    except Exception as exc:
        raise FileProcessingError(f"Text cleaning failed: {exc}") from exc

    # --- Step 3: Report type classification ---
    try:
        report_type, type_confidence = detect_report_type(cleaned_text)
    except Exception as exc:
        logger.exception("Report type detection failed, defaulting to unknown", report_id=report_id)
        report_type = None
        type_confidence = "low"

    # --- Step 4: Report date detection ---
    try:
        report_date, date_confidence = detect_report_date(cleaned_text)
    except Exception as exc:
        logger.exception("Report date detection failed", report_id=report_id)
        report_date = None
        date_confidence = "low"

    # --- Step 5: Assemble result ---
    elapsed_ms = (time.monotonic() - start_time) * 1000

    result = ReportResult(
        report_id=report_id,
        report_type=report_type,
        report_date=report_date,
        raw_text=cleaned_text,
        page_count=extraction_result.page_count,
        text_length=len(cleaned_text),
        processing_time_ms=round(elapsed_ms, 2),
        confidence=ReportConfidence(
            text_extraction=extraction_result.confidence,
            report_type_detection=type_confidence,
            report_date_detection=date_confidence,
        ),
        is_scanned_likely=extraction_result.is_scanned_likely,
    )

    logger.info(
        "Report processing complete",
        report_id=report_id,
        report_type=report_type,
        report_date=report_date,
        text_length=len(cleaned_text),
        page_count=extraction_result.page_count,
        processing_time_ms=round(elapsed_ms, 2),
        is_scanned_likely=extraction_result.is_scanned_likely,
    )

    return result
