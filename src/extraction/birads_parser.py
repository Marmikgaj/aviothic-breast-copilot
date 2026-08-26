"""BI-RADS assessment parser — extracts BI-RADS category, side, descriptor, and source spans.

Per AGENTS.md §1 & Rules.md §3, extraction is deterministic and fully auditable.
"""

from __future__ import annotations

import re

from src.api.schemas import BiradsEntity, SourceSpan
from src.core.logging import get_logger

logger = get_logger(__name__)

# BI-RADS Category patterns
_BIRADS_PATTERN = re.compile(
    r"\b(?:BI-?RADS|BIRADS)(?:\s+(?:Category|Assessment|Category:))?\s+([0-6]|[4][ABCabc])\b"
    r"(?:\s*[:-]?\s*([A-Za-z\s,]{4,50}))?",
    re.IGNORECASE,
)

# Known BI-RADS category descriptors
_CATEGORY_DESCRIPTORS = {
    "0": "Incomplete - Need Additional Imaging Evaluation",
    "1": "Negative",
    "2": "Benign",
    "3": "Probably Benign",
    "4": "Suspicious",
    "4A": "Low Suspicion for Malignancy",
    "4B": "Moderate Suspicion for Malignancy",
    "4C": "High Suspicion for Malignancy",
    "5": "Highly Suggestive of Malignancy",
    "6": "Known Biopsy-Proven Malignancy",
}


def parse_birads(text: str) -> list[BiradsEntity]:
    """Extract BI-RADS assessment entities with character source spans from raw/cleaned report text.

    Args:
        text: Cleaned report text.

    Returns:
        List of BiradsEntity instances found in the text.
    """
    entities: list[BiradsEntity] = []

    for match in _BIRADS_PATTERN.finditer(text):
        raw_cat = match.group(1).upper()
        raw_descriptor = match.group(2).strip() if match.group(2) else None

        if raw_descriptor:
            raw_descriptor = raw_descriptor.split("\n")[0].strip(" .,-")
            if len(raw_descriptor) < 3 or any(
                w in raw_descriptor.lower() for w in ["recommendation", "patient", "date", "signed"]
            ):
                raw_descriptor = None

        descriptor = raw_descriptor or _CATEGORY_DESCRIPTORS.get(raw_cat)

        start_char, end_char = match.span()
        snippet = match.group(0)
        context_start = max(0, start_char - 100)
        context_text = text[context_start:end_char].lower()

        if "left breast" in context_text or "left:" in context_text or "in the left" in context_text:
            side = "left"
        elif "right breast" in context_text or "right:" in context_text or "in the right" in context_text:
            side = "right"
        elif "bilateral" in context_text:
            side = "bilateral"
        else:
            side = "unspecified"

        confidence = 0.95 if raw_cat in _CATEGORY_DESCRIPTORS else 0.85

        entities.append(
            BiradsEntity(
                category=raw_cat,
                descriptor=descriptor,
                side=side,
                span=SourceSpan(
                    start_char=start_char,
                    end_char=end_char,
                    snippet=snippet,
                ),
                confidence=confidence,
            )
        )

    logger.debug("BI-RADS parsing complete", count=len(entities))
    return entities
