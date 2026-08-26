"""Entity extraction orchestrator engine — combines all clinical entity parsers into a unified interface.

Per AGENTS.md §1 & Rules.md §3, extraction is 100% deterministic, auditable, and trace-backed by source character spans.
"""

from __future__ import annotations

from src.api.schemas import ExtractedEntities
from src.core.logging import get_logger
from src.extraction.biomarker_parser import parse_biomarkers
from src.extraction.birads_parser import parse_birads
from src.extraction.lymph_parser import parse_lymph_nodes
from src.extraction.tnm_parser import parse_tnm_staging
from src.extraction.tumor_parser import parse_tumor_dimensions

logger = get_logger(__name__)


def extract_entities(text: str) -> ExtractedEntities:
    """Extract all structured clinical entities from cleaned report text.

    Args:
        text: Cleaned medical report text.

    Returns:
        An ``ExtractedEntities`` container holding all extracted entity models with character source spans.
    """
    if not text.strip():
        return ExtractedEntities()

    logger.debug("Starting entity extraction", text_length=len(text))

    birads = parse_birads(text)
    tnm = parse_tnm_staging(text)
    biomarkers = parse_biomarkers(text)
    tumors = parse_tumor_dimensions(text)
    lymph = parse_lymph_nodes(text)

    result = ExtractedEntities(
        birads=birads,
        tnm_staging=tnm,
        biomarkers=biomarkers,
        tumor_dimensions=tumors,
        lymph_nodes=lymph,
    )

    logger.info(
        "Entity extraction complete",
        birads_count=len(birads),
        tnm_count=len(tnm),
        biomarkers_count=len(biomarkers),
        tumor_dimensions_count=len(tumors),
        lymph_nodes_count=len(lymph),
    )

    return result
