"""Keyword/regex-based report type classification.

Deterministic and auditable (Rules.md — spaCy + custom rules philosophy
applied here for report type, which is a simpler classification task).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class _KeywordGroup:
    """A group of keywords associated with a report modality.

    Attributes:
        modality: The report modality name.
        keywords: Regex patterns to match (case-insensitive).
        weight: Scoring weight (higher-weight keywords are more discriminative).
    """

    modality: str
    keywords: list[re.Pattern[str]]
    weight: float = 1.0


# Keyword dictionaries organized by modality.
# Higher-weight keywords are more discriminative (less likely to appear in
# unrelated contexts).
_KEYWORD_GROUPS: list[_KeywordGroup] = [
    _KeywordGroup(
        modality="mammography",
        keywords=[
            re.compile(r"\bmammogra(?:m|phy|phic)\b", re.IGNORECASE),
            re.compile(r"\bbi-?rads?\b", re.IGNORECASE),
            re.compile(r"\bbreast\s+density\b", re.IGNORECASE),
            re.compile(r"\bcalcification[s]?\b", re.IGNORECASE),
            re.compile(r"\btomosynthesis\b", re.IGNORECASE),
            re.compile(r"\bcraniocaudal\b", re.IGNORECASE),
            re.compile(r"\bmediolateral\s+oblique\b", re.IGNORECASE),
            re.compile(r"\bscreening\s+mammogra", re.IGNORECASE),
            re.compile(r"\bdiagnostic\s+mammogra", re.IGNORECASE),
        ],
    ),
    _KeywordGroup(
        modality="ultrasound",
        keywords=[
            re.compile(r"\bultrasound\b", re.IGNORECASE),
            re.compile(r"\bsonograp(?:hy|hic|her)\b", re.IGNORECASE),
            re.compile(r"\bechogenic(?:ity)?\b", re.IGNORECASE),
            re.compile(r"\bhypoechoic\b", re.IGNORECASE),
            re.compile(r"\bhyperechoic\b", re.IGNORECASE),
            re.compile(r"\banechoic\b", re.IGNORECASE),
            re.compile(r"\bcyst(?:ic)?\b", re.IGNORECASE),
            re.compile(r"\bdoppler\b", re.IGNORECASE),
            re.compile(r"\btransducer\b", re.IGNORECASE),
        ],
    ),
    _KeywordGroup(
        modality="mri",
        keywords=[
            re.compile(r"\b(?:breast\s+)?mri\b", re.IGNORECASE),
            re.compile(r"\bmagnetic\s+resonance\b", re.IGNORECASE),
            re.compile(r"\bcontrast\s+enhance(?:ment|d)\b", re.IGNORECASE),
            re.compile(r"\bkinetic\s+curve\b", re.IGNORECASE),
            re.compile(r"\bdiffusion\s+weight(?:ed|ing)\b", re.IGNORECASE),
            re.compile(r"\bgadolinium\b", re.IGNORECASE),
            re.compile(r"\bT[12]\s*(?:weighted|W)\b", re.IGNORECASE),
            re.compile(r"\bDCE\b"),  # Dynamic contrast-enhanced
        ],
    ),
    _KeywordGroup(
        modality="pet_ct",
        keywords=[
            re.compile(r"\bPET[-/]?CT\b", re.IGNORECASE),
            re.compile(r"\bSUV\s*(?:max)?\b", re.IGNORECASE),
            re.compile(r"\bFDG\b", re.IGNORECASE),
            re.compile(r"\bmetabolic\s+activity\b", re.IGNORECASE),
            re.compile(r"\bhyperintense\s+uptake\b", re.IGNORECASE),
            re.compile(r"\btracer\s+uptake\b", re.IGNORECASE),
            re.compile(r"\bstandardized\s+uptake\b", re.IGNORECASE),
        ],
    ),
    _KeywordGroup(
        modality="pathology",
        keywords=[
            re.compile(r"\bpathology\b", re.IGNORECASE),
            re.compile(r"\bbiopsy\b", re.IGNORECASE),
            re.compile(r"\bhistolog(?:y|ic|ical)\b", re.IGNORECASE),
            re.compile(r"\bspecimen\b", re.IGNORECASE),
            re.compile(r"\bcarcinoma\b", re.IGNORECASE),
            re.compile(r"\binvasive\s+ductal\b", re.IGNORECASE),
            re.compile(r"\bin\s+situ\b", re.IGNORECASE),
            re.compile(r"\b(?:ER|PR)[\s/]+(?:positive|negative|pos|neg)\b", re.IGNORECASE),
            re.compile(r"\bHER[-\s]?2\b", re.IGNORECASE),
            re.compile(r"\bKi[-\s]?67\b", re.IGNORECASE),
            re.compile(r"\bimmunohistochem(?:istry|ical)\b", re.IGNORECASE),
            re.compile(r"\btumor\s+grade\b", re.IGNORECASE),
            re.compile(r"\bmitotic\b", re.IGNORECASE),
        ],
    ),
    _KeywordGroup(
        modality="discharge",
        keywords=[
            re.compile(r"\bdischarge\s+summar(?:y|ies)\b", re.IGNORECASE),
            re.compile(r"\bhospital\s+course\b", re.IGNORECASE),
            re.compile(r"\bdisposition\b", re.IGNORECASE),
            re.compile(r"\badmission\s+date\b", re.IGNORECASE),
            re.compile(r"\bdischarge\s+date\b", re.IGNORECASE),
            re.compile(r"\bdischarge\s+diagnosis\b", re.IGNORECASE),
            re.compile(r"\bdischarge\s+instructions?\b", re.IGNORECASE),
            re.compile(r"\bdischarge\s+medications?\b", re.IGNORECASE),
        ],
    ),
]


def detect_report_type(text: str) -> tuple[str | None, Literal["high", "medium", "low"]]:
    """Detect the report modality from the text content using keyword matching.

    Scans the text for modality-specific terms, scores each modality by
    weighted keyword hits, and returns the highest-scoring category.

    Confidence levels:
        - ``"high"``: Dominant category has ≥3 hits and ≥2× the runner-up.
        - ``"medium"``: Dominant category has ≥2 hits.
        - ``"low"``: Dominant category has <2 hits (ambiguous or unknown).

    Args:
        text: Cleaned report text.

    Returns:
        Tuple of ``(modality_name, confidence)``. Modality is ``None``
        if no category scores above the threshold.
    """
    if not text or not text.strip():
        return None, "low"

    # Score each modality.
    scores: dict[str, float] = {}
    hit_counts: dict[str, int] = {}

    for group in _KEYWORD_GROUPS:
        total_hits = 0
        for pattern in group.keywords:
            matches = pattern.findall(text)
            total_hits += len(matches)

        weighted_score = total_hits * group.weight
        scores[group.modality] = weighted_score
        hit_counts[group.modality] = total_hits

    # Sort by score descending.
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    if not ranked or ranked[0][1] == 0:
        logger.info("No modality keywords matched", text_length=len(text))
        return None, "low"

    best_modality, best_score = ranked[0]
    best_hits = hit_counts[best_modality]
    runner_up_score = ranked[1][1] if len(ranked) > 1 else 0

    # Determine confidence.
    if best_hits >= 3 and (runner_up_score == 0 or best_score >= runner_up_score * 2):
        confidence: Literal["high", "medium", "low"] = "high"
    elif best_hits >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    logger.info(
        "Report type detected",
        modality=best_modality,
        confidence=confidence,
        hits=best_hits,
        score=best_score,
        runner_up_score=runner_up_score,
    )

    return best_modality, confidence
