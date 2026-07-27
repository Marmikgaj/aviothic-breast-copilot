"""Report date extraction using regex pattern matching.

Looks for dates near context markers like "Date of Exam", "Report Date",
"Study Date", etc. Falls back to the first date-like pattern in the document.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from src.core.logging import get_logger

logger = get_logger(__name__)

# Context markers that indicate a date field in medical reports.
_DATE_CONTEXT_MARKERS = [
    r"date\s+of\s+(?:exam(?:ination)?|study|report|service|procedure)",
    r"(?:exam|study|report|service|procedure)\s+date",
    r"date\s*:",
    r"performed\s+(?:on|date)",
    r"dictated\s*:",
    r"signed\s*:",
]

# Date format patterns ordered from most specific to least specific.
# Each tuple: (regex_pattern, strptime_format)
_DATE_PATTERNS: list[tuple[str, str]] = [
    # ISO 8601: 2026-01-15
    (r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b", "%Y-%m-%d"),
    # US format: 01/15/2026 or 01-15-2026
    (r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", "%m-%d-%Y"),
    # US short: 01/15/26
    (r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2})\b", "%m-%d-%y"),
    # Written: January 15, 2026 or Jan 15, 2026
    (r"\b(\w+\s+\d{1,2},?\s+\d{4})\b", "%B %d, %Y"),
    # Written short month: 15 Jan 2026
    (r"\b(\d{1,2}\s+\w+\s+\d{4})\b", "%d %B %Y"),
]


def detect_report_date(text: str) -> tuple[str | None, Literal["high", "medium", "low"]]:
    """Detect the report date from the text content.

    Strategy:
        1. Search near context markers (e.g., "Date of Exam:") for high confidence.
        2. Fall back to the first date-like pattern in the document for low confidence.

    Args:
        text: Cleaned report text.

    Returns:
        Tuple of ``(iso_date_string, confidence)``. Date is ``None`` if
        no parseable date is found.
    """
    if not text or not text.strip():
        return None, "low"

    # --- Strategy 1: Look for dates near context markers (high confidence) ---
    for marker in _DATE_CONTEXT_MARKERS:
        # Build a pattern that captures text near the context marker.
        context_pattern = re.compile(
            rf"{marker}\s*[:\-]?\s*(.{{0,40}})",
            re.IGNORECASE,
        )
        context_match = context_pattern.search(text)
        if context_match:
            nearby_text = context_match.group(1)
            parsed_date = _try_parse_date(nearby_text)
            if parsed_date:
                logger.info(
                    "Report date found near context marker",
                    date=parsed_date,
                    marker=marker,
                )
                return parsed_date, "high"

    # --- Strategy 2: First date-like pattern anywhere in the document ---
    parsed_date = _try_parse_date(text)
    if parsed_date:
        logger.info("Report date found via fallback scan", date=parsed_date)
        return parsed_date, "low"

    logger.info("No report date detected")
    return None, "low"


def _try_parse_date(text: str) -> str | None:
    """Try to parse a date from the given text using known date patterns.

    Args:
        text: Text to scan for date patterns.

    Returns:
        ISO 8601 date string (``YYYY-MM-DD``) if a valid date is found,
        or ``None``.
    """
    for pattern_str, date_format in _DATE_PATTERNS:
        match = re.search(pattern_str, text)
        if match:
            raw_date = match.group(1)
            # Normalize separators for parsing.
            normalized = raw_date.replace("/", "-")
            # Remove comma if present (e.g., "January 15, 2026" → "January 15 2026").
            normalized_no_comma = normalized.replace(",", "")

            for fmt_variant in [date_format, date_format.replace("/", "-")]:
                try:
                    parsed = datetime.strptime(normalized_no_comma.strip(), fmt_variant)  # noqa: DTZ007
                    # Sanity check: year should be reasonable (1990-2100).
                    if 1990 <= parsed.year <= 2100:
                        return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue

            # Try with the original (unnormalized) too, in case format uses '/'.
            for fmt_variant in [date_format, date_format.replace("-", "/")]:
                try:
                    parsed = datetime.strptime(raw_date.replace(",", "").strip(), fmt_variant)  # noqa: DTZ007
                    if 1990 <= parsed.year <= 2100:
                        return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue

    return None
