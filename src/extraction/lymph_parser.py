"""Lymph node status parser — extracts node counts, sentinel status, extranodal extension, and source spans.

Per AGENTS.md §1 & Rules.md §3, extraction is deterministic and fully auditable.
"""

from __future__ import annotations

import re

from src.api.schemas import LymphNodeEntity, SourceSpan
from src.core.logging import get_logger

logger = get_logger(__name__)

# Lymph node patterns
# e.g., "2/5 nodes positive", "0 of 4 sentinel lymph nodes positive", "4 nodes examined, 1 positive"
_NODE_COUNT_PATTERN = re.compile(
    r"\b(\d{1,2})\s*(?:of|/)\s*(\d{1,2})\s*(?:sentinel\s+)?(?:lymph\s+)?nodes?\s*(positive|involved)?\b",
    re.IGNORECASE,
)

_NO_LYMPH_NODES_PATTERN = re.compile(
    r"\b(?:no\s+suspicious\s+axillary\s+lymphadenopathy|lymph\s+nodes\s+are\s+unremarkable|negative\s+for\s+metastasis)\b",
    re.IGNORECASE,
)


def parse_lymph_nodes(text: str) -> list[LymphNodeEntity]:
    """Extract lymph node status entities with source character spans.

    Args:
        text: Cleaned report text.

    Returns:
        List of LymphNodeEntity instances found in text.
    """
    entities: list[LymphNodeEntity] = []

    # 1. Parse node ratio patterns (e.g. 2/5 nodes positive)
    for match in _NODE_COUNT_PATTERN.finditer(text):
        snippet = match.group(0).strip()
        start_char, end_char = match.span()

        pos_val = int(match.group(1))
        exam_val = int(match.group(2))

        is_sentinel = "sentinel" in snippet.lower()
        extranodal = "extranodal" in text[max(0, start_char - 50) : min(len(text), end_char + 50)].lower()

        entities.append(
            LymphNodeEntity(
                nodes_examined=exam_val,
                nodes_positive=pos_val,
                sentinel_status=is_sentinel,
                extranodal_extension=extranodal if "extranodal" in text.lower() else None,
                span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                confidence=0.95,
            )
        )

    # 2. Parse explicit negative node mentions if no specific counts were parsed
    if not entities:
        for match in _NO_LYMPH_NODES_PATTERN.finditer(text):
            snippet = match.group(0).strip()
            start_char, end_char = match.span()

            entities.append(
                LymphNodeEntity(
                    nodes_examined=None,
                    nodes_positive=0,
                    sentinel_status=None,
                    extranodal_extension=False,
                    span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                    confidence=0.90,
                )
            )

    logger.debug("Lymph node parsing complete", count=len(entities))
    return entities
