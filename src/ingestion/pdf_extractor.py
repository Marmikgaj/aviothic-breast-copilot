"""PDF text extraction using PyMuPDF (primary) with pdfplumber (fallback).

If both extractors yield negligible text, the document is flagged as likely
scanned/image-based — OCR is deferred to Phase 2 (Phases.md §2).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

import fitz  # PyMuPDF
import pdfplumber

from src.core.logging import get_logger

logger = get_logger(__name__)

# Minimum character threshold below which we suspect the PDF is scanned/image-based.
_MIN_TEXT_THRESHOLD = 50


@dataclass(frozen=True)
class ExtractionResult:
    """Result of PDF text extraction.

    Attributes:
        raw_text: Extracted text (may be empty for scanned PDFs).
        page_count: Number of pages in the document.
        confidence: Confidence level of the extraction quality.
        is_scanned_likely: True if the document appears to be scanned/image-based.
        extraction_method: Which extractor produced the final text.
    """

    raw_text: str
    page_count: int
    confidence: Literal["high", "medium", "low"]
    is_scanned_likely: bool
    extraction_method: str


def extract_text(content: bytes) -> ExtractionResult:
    """Extract text from a PDF file.

    Uses PyMuPDF as the primary extractor. If PyMuPDF yields insufficient text,
    falls back to pdfplumber. If both yield negligible text, the document is
    flagged as likely scanned.

    Args:
        content: Raw bytes of the PDF file.

    Returns:
        An ``ExtractionResult`` with the extracted text and metadata.
    """
    # --- Try PyMuPDF first (fast, handles most text-native PDFs well) ---
    pymupdf_text, page_count = _extract_with_pymupdf(content)

    if len(pymupdf_text.strip()) >= _MIN_TEXT_THRESHOLD:
        confidence = _assess_confidence(pymupdf_text, page_count)
        logger.info(
            "Text extracted via PyMuPDF",
            page_count=page_count,
            text_length=len(pymupdf_text),
            confidence=confidence,
        )
        return ExtractionResult(
            raw_text=pymupdf_text,
            page_count=page_count,
            confidence=confidence,
            is_scanned_likely=False,
            extraction_method="pymupdf",
        )

    # --- Fallback to pdfplumber (better for table-heavy or complex layouts) ---
    logger.info("PyMuPDF yielded insufficient text, falling back to pdfplumber")
    pdfplumber_text, pdfplumber_page_count = _extract_with_pdfplumber(content)
    page_count = max(page_count, pdfplumber_page_count)

    if len(pdfplumber_text.strip()) >= _MIN_TEXT_THRESHOLD:
        confidence = _assess_confidence(pdfplumber_text, page_count)
        logger.info(
            "Text extracted via pdfplumber (fallback)",
            page_count=page_count,
            text_length=len(pdfplumber_text),
            confidence=confidence,
        )
        return ExtractionResult(
            raw_text=pdfplumber_text,
            page_count=page_count,
            confidence=confidence,
            is_scanned_likely=False,
            extraction_method="pdfplumber",
        )

    # --- Both extractors failed: likely a scanned/image-based document ---
    best_text = pymupdf_text if len(pymupdf_text) >= len(pdfplumber_text) else pdfplumber_text
    logger.warning(
        "Both extractors yielded negligible text — likely scanned document",
        page_count=page_count,
        pymupdf_length=len(pymupdf_text),
        pdfplumber_length=len(pdfplumber_text),
    )
    return ExtractionResult(
        raw_text=best_text,
        page_count=page_count,
        confidence="low",
        is_scanned_likely=True,
        extraction_method="none",
    )


def _extract_with_pymupdf(content: bytes) -> tuple[str, int]:
    """Extract text from all pages using PyMuPDF.

    Args:
        content: Raw PDF bytes.

    Returns:
        Tuple of (extracted_text, page_count).
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        pages: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text:
                pages.append(text)
        page_count = len(doc)
        doc.close()
        return "\n\n".join(pages), page_count
    except Exception:
        logger.exception("PyMuPDF extraction failed")
        return "", 0


def _extract_with_pdfplumber(content: bytes) -> tuple[str, int]:
    """Extract text from all pages using pdfplumber.

    Args:
        content: Raw PDF bytes.

    Returns:
        Tuple of (extracted_text, page_count).
    """
    try:
        pdf = pdfplumber.open(io.BytesIO(content))
        pages: list[str] = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        page_count = len(pdf.pages)
        pdf.close()
        return "\n\n".join(pages), page_count
    except Exception:
        logger.exception("pdfplumber extraction failed")
        return "", 0


def _assess_confidence(text: str, page_count: int) -> Literal["high", "medium", "low"]:
    """Assess the confidence level of the extracted text.

    Heuristic: a text-native PDF with readable content should yield a reasonable
    character-per-page ratio.

    Args:
        text: The extracted text.
        page_count: Number of pages in the document.

    Returns:
        Confidence level: ``"high"``, ``"medium"``, or ``"low"``.
    """
    if page_count == 0:
        return "low"

    chars_per_page = len(text.strip()) / page_count

    # A typical medical report page has ~1500-3000 characters.
    if chars_per_page >= 200:
        return "high"
    elif chars_per_page >= 50:
        return "medium"
    else:
        return "low"
