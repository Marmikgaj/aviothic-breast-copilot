"""Tests for the report date extractor."""

from __future__ import annotations

import pytest

from src.ingestion.date_extractor import detect_report_date


class TestDateExtractor:
    """Report date extractor test suite."""

    def test_date_with_context_marker_us_format(self) -> None:
        """'Date of Exam: MM/DD/YYYY' should be detected with high confidence."""
        text = "Date of Exam: 01/15/2026\nFindings: Normal."
        date, confidence = detect_report_date(text)
        assert date == "2026-01-15"
        assert confidence == "high"

    def test_date_with_study_date_marker(self) -> None:
        """'Study Date:' context marker should work."""
        text = "Study Date: 03/20/2026\nPatient: Jane Doe"
        date, confidence = detect_report_date(text)
        assert date == "2026-03-20"
        assert confidence == "high"

    def test_date_with_report_date_marker(self) -> None:
        """'Report Date:' context marker should work."""
        text = "Report Date: 02/05/2026\nPathologist: Dr. Smith"
        date, confidence = detect_report_date(text)
        assert date == "2026-02-05"
        assert confidence == "high"

    def test_date_iso_format(self) -> None:
        """ISO 8601 date should be parsed correctly."""
        text = "Date of Exam: 2026-01-15\nMore text."
        date, confidence = detect_report_date(text)
        assert date == "2026-01-15"
        assert confidence == "high"

    def test_date_without_context_marker(self) -> None:
        """A date without a context marker should be found with low confidence."""
        text = "This report was generated on 07/28/2026. No other context."
        date, confidence = detect_report_date(text)
        assert date is not None
        assert confidence == "low"

    def test_no_date_present(self) -> None:
        """Text without any dates should return None."""
        text = "No dates are mentioned in this text at all."
        date, confidence = detect_report_date(text)
        assert date is None
        assert confidence == "low"

    def test_empty_text(self) -> None:
        """Empty text should return None with low confidence."""
        date, confidence = detect_report_date("")
        assert date is None
        assert confidence == "low"

    def test_date_with_procedure_date_marker(self) -> None:
        """'Date of Procedure:' should be recognized."""
        text = "Date of Procedure: 02/01/2026\nSpecimen: Left breast."
        date, confidence = detect_report_date(text)
        assert date == "2026-02-01"
        assert confidence == "high"

    def test_date_from_realistic_report(self, sample_plain_text_content: str) -> None:
        """The shared fixture should have a detectable date."""
        date, confidence = detect_report_date(sample_plain_text_content)
        assert date is not None
        # The fixture has "Date of Exam: 03/20/2026"
        assert date == "2026-03-20"
        assert confidence == "high"

    def test_rejects_unreasonable_year(self) -> None:
        """Dates with unreasonable years should be rejected."""
        text = "Date of Exam: 01/15/1800\nSome old text."
        date, confidence = detect_report_date(text)
        # Year 1800 is outside the 1990-2100 sanity range.
        # Should either return None or find a different date.
        if date is not None:
            year = int(date.split("-")[0])
            assert 1990 <= year <= 2100
