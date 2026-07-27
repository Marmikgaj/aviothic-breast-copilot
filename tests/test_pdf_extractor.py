"""Tests for the PDF text extractor."""

from __future__ import annotations

import pytest

from src.ingestion.pdf_extractor import ExtractionResult, extract_text


class TestPdfExtractor:
    """PDF text extraction test suite."""

    def test_extract_text_native_pdf(self, sample_mammography_pdf: bytes) -> None:
        """Text-native PDF should yield text with high confidence."""
        result = extract_text(sample_mammography_pdf)

        assert isinstance(result, ExtractionResult)
        assert len(result.raw_text.strip()) > 100
        assert result.page_count >= 1
        assert result.confidence in ("high", "medium")
        assert result.is_scanned_likely is False
        assert result.extraction_method in ("pymupdf", "pdfplumber")

    def test_extract_text_contains_expected_content(self, sample_mammography_pdf: bytes) -> None:
        """Extracted text should contain key terms from the synthetic report."""
        result = extract_text(sample_mammography_pdf)

        text = result.raw_text.lower()
        assert "mammography" in text or "mammogram" in text
        assert "bi-rads" in text.replace(" ", "") or "birads" in text

    def test_extract_scanned_pdf_detection(self) -> None:
        """A minimal PDF with no text should be flagged as likely scanned."""
        from fpdf import FPDF

        # Create a PDF with only an image placeholder (no text).
        pdf = FPDF()
        pdf.add_page()
        # Add a tiny colored rectangle instead of text.
        pdf.set_fill_color(200, 200, 200)
        pdf.rect(10, 10, 50, 50, style="F")
        content = pdf.output()

        result = extract_text(content)

        assert result.is_scanned_likely is True
        assert result.confidence == "low"

    def test_extract_pathology_pdf(self, sample_pathology_pdf: bytes) -> None:
        """Pathology report PDF should be extractable."""
        result = extract_text(sample_pathology_pdf)

        assert len(result.raw_text.strip()) > 100
        assert result.page_count >= 1
        assert result.is_scanned_likely is False

        text = result.raw_text.lower()
        assert "pathology" in text
