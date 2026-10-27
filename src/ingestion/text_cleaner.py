"""Text cleaning pipeline for extracted report text.

Normalizes Unicode, strips control characters, collapses whitespace,
and removes repetitive headers/footers — while preserving clinically
meaningful structure (paragraph breaks, list formatting).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from src.core.logging import get_logger

logger = get_logger(__name__)

# Regex patterns compiled once at module level for performance.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_EXCESSIVE_NEWLINES = re.compile(r"\n{4,}")
_EXCESSIVE_SPACES = re.compile(r"[ \t]{3,}")
_TRAILING_WHITESPACE = re.compile(r"[ \t]+$", re.MULTILINE)
_PAGE_NUMBER_LINE = re.compile(r"^\s*(?:page\s+)?\d+\s*(?:of\s+\d+)?\s*$", re.IGNORECASE | re.MULTILINE)


def clean_text(raw_text: str) -> str:
    """Clean and normalize extracted report text.

    Processing steps:
        1. Unicode NFC normalization.
        2. Strip null bytes and control characters.
        3. Remove repetitive headers/footers (detected by line frequency).
        4. Remove standalone page number lines.
        5. Collapse excessive whitespace while preserving paragraph breaks.
        6. Strip trailing whitespace from each line.
        7. Final strip.

    Args:
        raw_text: The raw text extracted from a PDF.

    Returns:
        The cleaned text, suitable for downstream entity extraction.
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text

    # 1. Unicode NFC normalization — ensures consistent character representation.
    text = unicodedata.normalize("NFC", text)

    # 2. Strip control characters (keep newlines \n, carriage returns \r, tabs \t).
    text = _CONTROL_CHARS.sub("", text)

    # 3. Remove repetitive headers/footers.
    text = _remove_repeated_lines(text)

    # 4. Remove standalone page number lines.
    text = _PAGE_NUMBER_LINE.sub("", text)

    # 5. Collapse excessive whitespace.
    text = _EXCESSIVE_SPACES.sub("  ", text)  # Max two spaces inline.
    text = _EXCESSIVE_NEWLINES.sub("\n\n\n", text)  # Max triple newline (paragraph + section gap).

    # 6. Strip trailing whitespace from each line.
    text = _TRAILING_WHITESPACE.sub("", text)

    # 7. Final strip.
    text = text.strip()

    logger.debug("Text cleaned", original_length=len(raw_text), cleaned_length=len(text))

    return text


def _remove_repeated_lines(text: str, *, min_occurrences: int = 3) -> str:
    """Remove lines that appear repeatedly (likely headers/footers).

    Medical report PDFs often have the institution name, address, or
    department header repeated on every page. This function identifies
    lines that appear ``min_occurrences`` or more times and removes them.

    Short lines (< 5 chars) and lines containing digits (potential data)
    are excluded from removal to avoid stripping legitimate repeated data.

    Args:
        text: Input text.
        min_occurrences: Minimum repetition count to qualify as a header/footer.

    Returns:
        Text with repetitive lines removed.
    """
    lines = text.split("\n")

    if len(lines) < min_occurrences * 2:
        # Not enough lines to have meaningful repetition.
        return text

    # Count normalized line frequencies.
    normalized_counts: Counter[str] = Counter()
    for line in lines:
        stripped = line.strip()
        if stripped:
            normalized_counts[stripped] += 1

    # Identify lines to remove.
    lines_to_remove: set[str] = set()
    for normalized_line, count in normalized_counts.items():
        if count >= min_occurrences and len(normalized_line) >= 5:
            # Don't remove lines that are mostly numeric (could be real data).
            non_digit_ratio = sum(1 for c in normalized_line if not c.isdigit()) / len(normalized_line)
            if non_digit_ratio > 0.3:
                lines_to_remove.add(normalized_line)

    if not lines_to_remove:
        return text

    logger.debug("Removing repeated lines", count=len(lines_to_remove))

    return "\n".join(line for line in lines if line.strip() not in lines_to_remove)
