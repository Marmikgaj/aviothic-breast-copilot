"""TNM staging parser — extracts pathological and clinical T, N, M staging entities and spans.

Per AGENTS.md §1 & Rules.md §3, extraction is deterministic and fully auditable.
"""

from __future__ import annotations

import re

from src.api.schemas import SourceSpan, TnmEntity
from src.core.logging import get_logger

logger = get_logger(__name__)

# TNM Staging pattern
_TNM_STAGE_PATTERN = re.compile(
    r"\b([pc]?)T(is|[0-4][a-c]?)\b(?:\s*\(.*?\))?\s*" r"(?:([pc]?)N([0-3][a-c]?)\b)?\s*" r"(?:([pc]?)M([01][a-c]?)\b)?",
    re.IGNORECASE,
)


def parse_tnm_staging(text: str) -> list[TnmEntity]:
    """Extract TNM staging entities with character source spans from report text.

    Args:
        text: Cleaned report text.

    Returns:
        List of TnmEntity instances found in the text.
    """
    entities: list[TnmEntity] = []

    for match in _TNM_STAGE_PATTERN.finditer(text):
        snippet = match.group(0).strip()
        start_char, end_char = match.span()

        t_prefix = match.group(1).lower() if match.group(1) else ""
        t_val = match.group(2)
        n_prefix = match.group(3).lower() if match.group(3) else ""
        n_val = match.group(4)
        m_prefix = match.group(5).lower() if match.group(5) else ""
        m_val = match.group(6)

        if not t_val:
            continue

        if len(snippet) < 3 and not t_prefix:
            continue

        t_stage = f"{t_prefix}T{t_val}" if t_prefix else f"T{t_val}"
        n_stage = f"{n_prefix}N{n_val}" if n_val else None
        m_stage = f"{m_prefix}M{m_val}" if m_val else None

        is_pathological = t_prefix == "p" or n_prefix == "p" or m_prefix == "p"

        entities.append(
            TnmEntity(
                raw_stage=snippet,
                t_stage=t_stage,
                n_stage=n_stage,
                m_stage=m_stage,
                is_pathological=is_pathological,
                span=SourceSpan(
                    start_char=start_char,
                    end_char=end_char,
                    snippet=snippet,
                ),
                confidence=0.95 if (n_val or m_val or t_prefix) else 0.85,
            )
        )

    logger.debug("TNM staging parsing complete", count=len(entities))
    return entities
