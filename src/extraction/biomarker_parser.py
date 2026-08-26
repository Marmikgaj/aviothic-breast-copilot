"""Biomarker parser — extracts ER, PR, HER2, and Ki-67 statuses, percentages, IHC scores, and source spans.

Per AGENTS.md §1 & Rules.md §3, extraction is deterministic and fully auditable.
"""

from __future__ import annotations

import re

from src.api.schemas import BiomarkerEntity, SourceSpan
from src.core.logging import get_logger

logger = get_logger(__name__)

# Biomarker patterns
_ER_PATTERN = re.compile(
    r"\b(?:Estrogen\s+Receptor(?:\s*\(\s*ER\s*\))?|ER)\b\s*[:=\-]?\s*"
    r"(POSITIVE|NEGATIVE|EQUIVOCAL|Positive|Negative|Equivocal)?\s*"
    r"(?:\(\s*(\d{1,3})%\s*(?:nuclear\s+staining|of\s+tumor\s+nuclei)?(?:[,\s]+(strong|moderate|weak)\s+intensity)?\)?|\s*(\d{1,3})%)?",
    re.IGNORECASE,
)

_PR_PATTERN = re.compile(
    r"\b(?:Progesterone\s+Receptor(?:\s*\(\s*PR\s*\))?|PR)\b\s*[:=\-]?\s*"
    r"(POSITIVE|NEGATIVE|EQUIVOCAL|Positive|Negative|Equivocal)?\s*"
    r"(?:\(\s*(\d{1,3})%\s*(?:nuclear\s+staining|of\s+tumor\s+nuclei)?(?:[,\s]+(strong|moderate|weak)\s+intensity)?\)?|\s*(\d{1,3})%)?",
    re.IGNORECASE,
)

_HER2_PATTERN = re.compile(
    r"\b(?:HER2(?:\s*/\s*neu)?(?:\s+Status)?|HER-2)\b\s*[:=\-]?\s*"
    r"(POSITIVE|NEGATIVE|EQUIVOCAL|Positive|Negative|Equivocal)?\s*"
    r"(?:\(\s*(?:Score\s*)?(0|1\+|2\+|3\+)(?:\s+by\s+IHC)?\)?|\s*(?:Score\s*)?(0|1\+|2\+|3\+))?"
    r"(?:[,\s]+FISH\s*[:=\-]?\s*(amplified|non-amplified|equivocal))?",
    re.IGNORECASE,
)

_KI67_PATTERN = re.compile(
    r"\b(?:Ki-?67(?:\s+Proliferation\s+Index)?)\b\s*[:=\-]?\s*"
    r"(\d{1,3})%\s*"
    r"(?:\(\s*(low|intermediate|high)\s*(?:proliferative\s+index)?\)?)?",
    re.IGNORECASE,
)


def parse_biomarkers(text: str) -> list[BiomarkerEntity]:
    """Extract biomarker profile entities (ER, PR, HER2, Ki-67) with character source spans.

    Args:
        text: Cleaned report text.

    Returns:
        List of BiomarkerEntity instances found in text.
    """
    entities: list[BiomarkerEntity] = []

    # 1. Parse ER
    for match in _ER_PATTERN.finditer(text):
        snippet = match.group(0).strip()
        start_char, end_char = match.span()

        raw_status = (match.group(1) or "").lower()
        pct_str = match.group(2) or match.group(4)
        intensity_str = (match.group(3) or "").lower()

        status = _normalize_status(raw_status, pct_str)
        percentage = float(pct_str) if pct_str else None
        intensity = _normalize_intensity(intensity_str)

        entities.append(
            BiomarkerEntity(
                name="ER",
                status=status,
                percentage=percentage,
                intensity=intensity,
                span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                confidence=0.95 if raw_status or percentage is not None else 0.85,
            )
        )

    # 2. Parse PR
    for match in _PR_PATTERN.finditer(text):
        snippet = match.group(0).strip()
        start_char, end_char = match.span()

        raw_status = (match.group(1) or "").lower()
        pct_str = match.group(2) or match.group(4)
        intensity_str = (match.group(3) or "").lower()

        status = _normalize_status(raw_status, pct_str)
        percentage = float(pct_str) if pct_str else None
        intensity = _normalize_intensity(intensity_str)

        entities.append(
            BiomarkerEntity(
                name="PR",
                status=status,
                percentage=percentage,
                intensity=intensity,
                span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                confidence=0.95 if raw_status or percentage is not None else 0.85,
            )
        )

    # 3. Parse HER2
    for match in _HER2_PATTERN.finditer(text):
        snippet = match.group(0).strip()
        start_char, end_char = match.span()

        raw_status = (match.group(1) or "").lower()
        ihc_score = match.group(2) or match.group(3)
        fish_str = (match.group(4) or "").lower()

        status = _normalize_status(raw_status, None)
        if status == "unknown" and ihc_score:
            if ihc_score in ("0", "1+"):
                status = "negative"
            elif ihc_score == "3+":
                status = "positive"
            elif ihc_score == "2+":
                status = "equivocal"

        fish_status = "not_performed"
        if fish_str == "amplified":
            fish_status = "amplified"
        elif fish_str == "non-amplified":
            fish_status = "non-amplified"
        elif fish_str == "equivocal":
            fish_status = "equivocal"

        entities.append(
            BiomarkerEntity(
                name="HER2",
                status=status,
                ihc_score=ihc_score,
                fish_status=fish_status,
                span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                confidence=0.95 if status != "unknown" or ihc_score else 0.85,
            )
        )

    # 4. Parse Ki-67
    for match in _KI67_PATTERN.finditer(text):
        snippet = match.group(0).strip()
        start_char, end_char = match.span()

        pct_str = match.group(1)
        percentage = float(pct_str) if pct_str else None

        status = "positive" if (percentage and percentage > 0) else "negative"

        entities.append(
            BiomarkerEntity(
                name="Ki-67",
                status=status,
                percentage=percentage,
                span=SourceSpan(start_char=start_char, end_char=end_char, snippet=snippet),
                confidence=0.95,
            )
        )

    logger.debug("Biomarker parsing complete", count=len(entities))
    return entities


def _normalize_status(raw_status: str, pct_str: str | None) -> str:
    if "positive" in raw_status:
        return "positive"
    if "negative" in raw_status:
        return "negative"
    if "equivocal" in raw_status:
        return "equivocal"
    if pct_str:
        return "positive" if float(pct_str) > 0 else "negative"
    return "unknown"


def _normalize_intensity(intensity_str: str) -> str:
    if "strong" in intensity_str:
        return "strong"
    if "moderate" in intensity_str:
        return "moderate"
    if "weak" in intensity_str:
        return "weak"
    if "none" in intensity_str:
        return "none"
    return "unknown"
