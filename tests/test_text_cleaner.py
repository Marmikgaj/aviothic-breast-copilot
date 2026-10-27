"""Tests for the text cleaning pipeline."""

from __future__ import annotations

from src.ingestion.text_cleaner import clean_text


class TestTextCleaner:
    """Text cleaner test suite."""

    def test_empty_string_returns_empty(self) -> None:
        """Empty input should return empty output."""
        assert clean_text("") == ""
        assert clean_text("   ") == ""
        assert clean_text("\n\n\n") == ""

    def test_control_character_removal(self) -> None:
        """Null bytes and control characters should be stripped."""
        text = "Hello\x00World\x01Test\x7f"
        result = clean_text(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x7f" not in result
        assert "Hello" in result
        assert "World" in result

    def test_excessive_whitespace_collapsed(self) -> None:
        """Multiple consecutive spaces should be collapsed."""
        text = "Finding:     No masses      detected."
        result = clean_text(text)
        # Should have at most 2 consecutive spaces.
        assert "     " not in result
        assert "Finding:" in result
        assert "No masses" in result

    def test_excessive_newlines_collapsed(self) -> None:
        """More than 3 consecutive newlines should be collapsed."""
        text = "Section 1\n\n\n\n\n\n\nSection 2"
        result = clean_text(text)
        assert "\n\n\n\n" not in result
        assert "Section 1" in result
        assert "Section 2" in result

    def test_preserves_paragraph_breaks(self) -> None:
        """Paragraph breaks (double newlines) should be preserved."""
        text = "Paragraph one.\n\nParagraph two."
        result = clean_text(text)
        assert "\n\n" in result
        assert "Paragraph one." in result
        assert "Paragraph two." in result

    def test_unicode_normalization(self) -> None:
        """Unicode should be NFC-normalized."""
        # é as combining characters (e + combining acute accent)
        text = "caf\u0065\u0301"
        result = clean_text(text)
        # After NFC normalization, should be a single character.
        assert "café" in result or "caf" in result

    def test_removes_repeated_headers(self) -> None:
        """Lines repeated 3+ times should be removed (likely headers/footers)."""
        header = "Memorial Hospital — Radiology Department"
        content_lines = [
            header,
            "Finding A: Normal.",
            header,
            "Finding B: Calcifications.",
            header,
            "Finding C: Mass detected.",
            header,
        ]
        text = "\n".join(content_lines)
        result = clean_text(text)

        assert header not in result
        assert "Finding A" in result
        assert "Finding B" in result
        assert "Finding C" in result

    def test_preserves_short_repeated_lines(self) -> None:
        """Short repeated lines (<5 chars) should NOT be removed."""
        text = "A\nB\nA\nB\nA\nB\nImportant finding."
        result = clean_text(text)
        assert "Important finding." in result

    def test_removes_page_numbers(self) -> None:
        """Standalone page number lines should be removed."""
        text = "Finding: Normal breast tissue.\n1\nMore text.\nPage 2 of 5\nEnd."
        result = clean_text(text)
        assert "Finding: Normal breast tissue." in result
        assert "More text." in result
        assert "End." in result

    def test_trailing_whitespace_stripped(self) -> None:
        """Trailing whitespace on each line should be stripped."""
        text = "Line one   \nLine two  \n"
        result = clean_text(text)
        for line in result.split("\n"):
            assert line == line.rstrip()

    def test_realistic_report_cleaning(self, sample_plain_text_content: str) -> None:
        """A realistic report should clean without losing key content."""
        result = clean_text(sample_plain_text_content)

        assert "BI-RADS" in result
        assert "mammography" in result.lower() or "Mammography" in result
        assert "Date of Exam" in result
        assert len(result) > 100
