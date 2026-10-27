"""OCR engine — extracts text from scanned/image-based PDFs via Tesseract.

Called only when the primary PDF extractor flags ``is_scanned_likely=True``.
Uses PyMuPDF to render each page to a PNG image, then feeds it through
pytesseract. Returns a mean confidence score across all recognised words.

If the Tesseract binary is absent, raises ``OcrUnavailableError`` so the
pipeline can degrade gracefully rather than crash (Rules.md §4).
"""

from __future__ import annotations

import io
import statistics
from dataclasses import dataclass

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from src.core.exceptions import OcrUnavailableError
from src.core.logging import get_logger

logger = get_logger(__name__)

# DPI for page rendering — 150 is a good balance of quality vs. speed for
# typical A4 clinical reports. Higher values improve accuracy on small fonts
# but increase memory and processing time.
_RENDER_DPI = 150
_MATRIX = fitz.Matrix(_RENDER_DPI / 72, _RENDER_DPI / 72)

# Confidence below this threshold triggers a low-confidence warning.
_LOW_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class OcrResult:
    """Result of an OCR pass over a scanned PDF.

    Attributes:
        text: Aggregated text extracted from all pages.
        confidence: Mean word-level confidence in [0.0, 1.0].
                    0.0 means no words were detected.
        page_count: Number of pages processed.
    """

    text: str
    confidence: float
    page_count: int


def perform_ocr(content: bytes) -> OcrResult:
    """Run Tesseract OCR over every page of a PDF.

    Renders each page to a PNG image at ``_RENDER_DPI`` and extracts text
    via pytesseract. Word-level confidence scores are averaged to produce a
    single document-level confidence.

    Args:
        content: Raw bytes of the PDF file.

    Returns:
        An ``OcrResult`` with aggregated text and mean confidence.

    Raises:
        OcrUnavailableError: If the Tesseract binary is not found on PATH.
    """
    # Open the PDF with PyMuPDF.
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        logger.exception("Failed to open PDF for OCR rendering")
        raise OcrUnavailableError() from exc

    page_count = len(doc)
    pages_text: list[str] = []
    all_confidences: list[float] = []

    for page_index, page in enumerate(doc):
        page_text, page_confidences = _ocr_page(page, page_index)
        if page_text.strip():
            pages_text.append(page_text)
        all_confidences.extend(page_confidences)

    doc.close()

    aggregated_text = "\n\n".join(pages_text)
    mean_confidence = statistics.mean(all_confidences) / 100.0 if all_confidences else 0.0

    logger.info(
        "OCR complete",
        page_count=page_count,
        text_length=len(aggregated_text),
        mean_confidence=round(mean_confidence, 3),
    )

    return OcrResult(
        text=aggregated_text,
        confidence=round(mean_confidence, 3),
        page_count=page_count,
    )


def _ocr_page(page: fitz.Page, page_index: int) -> tuple[str, list[float]]:
    """Render a single page and extract text + per-word confidence scores.

    Args:
        page: PyMuPDF page object.
        page_index: Zero-based page index (for logging).

    Returns:
        Tuple of (extracted_text, list_of_word_confidences).

    Raises:
        OcrUnavailableError: If pytesseract raises TesseractNotFoundError.
    """
    # Render page to PNG bytes.
    pixmap = page.get_pixmap(matrix=_MATRIX)
    png_bytes = pixmap.tobytes(output="png")
    image = Image.open(io.BytesIO(png_bytes))

    try:
        # image_to_data returns per-word bounding boxes + confidence values.
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as exc:
        logger.warning("Tesseract binary not found — OCR unavailable")
        raise OcrUnavailableError() from exc
    except Exception:
        logger.exception("pytesseract failed on page %d", page_index)
        return "", []

    # Collect confidences for words with valid detections (conf > 0).
    confidences: list[float] = [float(c) for c in data["conf"] if isinstance(c, (int, float)) and c >= 0]

    logger.debug(
        "OCR page processed",
        page_index=page_index,
        word_count=len(confidences),
        mean_confidence=round(statistics.mean(confidences) / 100.0, 3) if confidences else 0.0,
    )

    return text, confidences
