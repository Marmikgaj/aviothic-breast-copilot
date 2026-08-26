"""Tumor dimension & anatomical location parser — extracts lesion sizes, 3D measurements, quadrants, clock positions, and source spans.

Per AGENTS.md §1 & Rules.md §3, extraction is deterministic and fully auditable.
"""

from __future__ import annotations

import re

from src.api.schemas import SourceSpan, TumorDimensionEntity
from src.core.logging import get_logger

logger = get_logger(__name__)

# Multi-dimensional size pattern: "1.6 x 1.4 x 1.5 cm", "14 x 11 x 13 mm", "8 mm", "1.4 cm"
_DIMENSION_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:x|×)\s*(\d+(?:\.\d+)?)(?:\s*(?:x|×)\s*(\d+(?:\.\d+)?))?\s*(cm|mm)\b",
    re.IGNORECASE,
)

_SINGLE_SIZE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(cm|mm)\s+(?:mass|lesion|nodule|tumor|calcifications|area)\b",
    re.IGNORECASE,
)

# Location patterns
_QUADRANT_PATTERN = re.compile(
    r"\b(upper\s+outer|upper\s+inner|lower\s+outer|lower\s+inner|central|subareolar)\s+quadrant\b",
    re.IGNORECASE,
)

_CLOCK_PATTERN = re.compile(
    r"\b([1-9]|1[0-2])\s*o['’]?clock(?:\s+position)?\b",
    re.IGNORECASE,
)


def parse_tumor_dimensions(text: str) -> list[TumorDimensionEntity]:
    """Extract tumor dimension and location entities with source character spans.

    Args:
        text: Cleaned report text.

    Returns:
        List of TumorDimensionEntity instances found in text.
    """
    entities: list[TumorDimensionEntity] = []

    # 1. Parse multi-dimensional sizes (e.g., 1.6 x 1.4 x 1.5 cm)
    for match in _DIMENSION_PATTERN.finditer(text):
        snippet = match.group(0).strip()
        start_char, end_char = match.span()

        d1 = float(match.group(1))
        d2 = float(match.group(2))
        d3 = float(match.group(3)) if match.group(3) else None
        unit = match.group(4).lower()

        # Convert to mm
        scale = 10.0 if unit == "cm" else 1.0
        dims_mm = [round(d1 * scale, 1), round(d2 * scale, 1)]
        if d3 is not None:
            dims_mm.append(round(d3 * scale, 1))

        primary_size_mm = max(dims_mm)

        # Context search for location (quadrant & clock position within 100 chars context)
        context_start = max(0, start_char - 100)
        context_end = min(len(text), end_char + 100)
        context_text = text[context_start:context_end]

        quad_match = _QUADRANT_PATTERN.search(context_text)
        quadrant = quad_match.group(0).strip() if quad_match else None

        clock_match = _CLOCK_PATTERN.search(context_text)
        clock_pos = clock_match.group(0).strip() if clock_match else None

        entities.append(
            TumorDimensionEntity(
                primary_size_mm=primary_size_mm,
                dimensions_mm=dims_mm,
                location_quadrant=quadrant,
                clock_position=clock_pos,
                span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                confidence=0.95,
            )
        )

    # 2. Parse single dimension pattern (e.g. 1.4 cm mass) if not overlapping multi-dimensional match
    for match in _SINGLE_SIZE_PATTERN.finditer(text):
        start_char, end_char = match.span()

        # Skip if already captured in a multi-dimensional span
        if any(e.span.start_char <= start_char and end_char <= e.span.end_char for e in entities):
            continue

        snippet = match.group(0).strip()
        val = float(match.group(1))
        unit = match.group(2).lower()
        size_mm = round(val * 10.0 if unit == "cm" else val, 1)

        context_start = max(0, start_char - 100)
        context_end = min(len(text), end_char + 100)
        context_text = text[context_start:context_end]

        quad_match = _QUADRANT_PATTERN.search(context_text)
        quadrant = quad_match.group(0).strip() if quad_match else None

        clock_match = _CLOCK_PATTERN.search(context_text)
        clock_pos = clock_match.group(0).strip() if clock_match else None

        entities.append(
            TumorDimensionEntity(
                primary_size_mm=size_mm,
                dimensions_mm=[size_mm],
                location_quadrant=quadrant,
                clock_position=clock_pos,
                span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                confidence=0.90,
            )
        )

    logger.debug("Tumor dimensions parsing complete", count=len(entities))
    return entities
