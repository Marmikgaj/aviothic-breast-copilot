"""Tests for the OCR engine.

All pytesseract calls are mocked — the Tesseract binary is not required at
test time (Rules.md §2 — no system dependencies required in CI).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import OcrUnavailableError
from src.ingestion.ocr_engine import OcrResult, perform_ocr


def _make_minimal_scanned_pdf() -> bytes:
    """Return a minimal PDF with no selectable text (image-only placeholder)."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(200, 200, 200)
    pdf.rect(10, 10, 100, 100, style="F")
    return bytes(pdf.output())


class TestOcrEngine:
    """Unit tests for the OCR engine (Tesseract mocked throughout)."""

    @patch("src.ingestion.ocr_engine.pytesseract.image_to_data")
    @patch("src.ingestion.ocr_engine.pytesseract.image_to_string")
    def test_perform_ocr_returns_ocr_result(self, mock_to_string: MagicMock, mock_to_data: MagicMock) -> None:
        """perform_ocr should return an OcrResult with correct types."""
        mock_to_string.return_value = "BREAST IMAGING REPORT\nBI-RADS Category 3"
        mock_to_data.return_value = {"conf": [92, 88, 75, 95, 80]}

        pdf_bytes = _make_minimal_scanned_pdf()
        result = perform_ocr(pdf_bytes)

        assert isinstance(result, OcrResult)
        assert isinstance(result.text, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.page_count, int)
        assert 0.0 <= result.confidence <= 1.0
        assert result.page_count >= 1

    @patch("src.ingestion.ocr_engine.pytesseract.image_to_data")
    @patch("src.ingestion.ocr_engine.pytesseract.image_to_string")
    def test_perform_ocr_high_confidence(self, mock_to_string: MagicMock, mock_to_data: MagicMock) -> None:
        """High word-confidence values should produce a confidence score >= 0.75."""
        mock_to_string.return_value = "Clear readable text from a well-scanned document."
        mock_to_data.return_value = {"conf": [95, 97, 92, 96, 91]}  # mean 94.2 → 0.942

        pdf_bytes = _make_minimal_scanned_pdf()
        result = perform_ocr(pdf_bytes)

        assert result.confidence >= 0.75
        assert len(result.text) > 0

    @patch("src.ingestion.ocr_engine.pytesseract.image_to_data")
    @patch("src.ingestion.ocr_engine.pytesseract.image_to_string")
    def test_perform_ocr_low_confidence(self, mock_to_string: MagicMock, mock_to_data: MagicMock) -> None:
        """Low word-confidence values should produce a confidence score < 0.5."""
        mock_to_string.return_value = "x@# g4rb!ge t3xt fr0m p00r sc4n"
        mock_to_data.return_value = {"conf": [10, 8, 15, 5, 12]}  # mean 10 → 0.1

        pdf_bytes = _make_minimal_scanned_pdf()
        result = perform_ocr(pdf_bytes)

        assert result.confidence < 0.5

    @patch("src.ingestion.ocr_engine.pytesseract.image_to_string")
    def test_perform_ocr_raises_ocr_unavailable_when_tesseract_missing(self, mock_to_string: MagicMock) -> None:
        """OcrUnavailableError must be raised if the Tesseract binary is absent."""
        import pytesseract as _pt

        mock_to_string.side_effect = _pt.TesseractNotFoundError()

        pdf_bytes = _make_minimal_scanned_pdf()

        with pytest.raises(OcrUnavailableError):
            perform_ocr(pdf_bytes)

    @patch("src.ingestion.ocr_engine.pytesseract.image_to_data")
    @patch("src.ingestion.ocr_engine.pytesseract.image_to_string")
    def test_perform_ocr_empty_confidence_list(self, mock_to_string: MagicMock, mock_to_data: MagicMock) -> None:
        """When no valid confidence values are returned, confidence should be 0.0."""
        mock_to_string.return_value = ""
        mock_to_data.return_value = {"conf": [-1, -1, -1]}  # all invalid

        pdf_bytes = _make_minimal_scanned_pdf()
        result = perform_ocr(pdf_bytes)

        assert result.confidence == 0.0
