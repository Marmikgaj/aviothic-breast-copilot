"""Citation formatting, provenance verification, and bibliography generation.

Enforces auditable grounding back to retrieved guidelines or PubMed literature
per ADR-006 and Rules.md §8.
"""

from __future__ import annotations

import re

from src.rag.schemas import RetrievedPassage

# Citation reference patterns: e.g. [1], [2], [NCCN 2024], [PMID: 29535039]
_CITATION_BRACKET_PATTERN = re.compile(r"\[([0-9]+|[A-Za-z0-9_/.\s-]+)\]")
_PMID_PATTERN = re.compile(r"\bPMID:\s*([0-9]+)\b", re.IGNORECASE)


def generate_bibliography(passages: list[RetrievedPassage]) -> str:
    """Format retrieved passages into a standardized clinical bibliography.

    Args:
        passages: List of retrieved passages used to ground a response.

    Returns:
        Formatted bibliography string with numbered references.
    """
    if not passages:
        return ""

    lines: list[str] = ["\n### Clinical References & Guideline Citations\n"]
    seen_docs: set[str] = set()
    ref_idx = 1

    for passage in passages:
        if passage.document_id in seen_docs:
            continue
        seen_docs.add(passage.document_id)

        meta = passage.metadata
        authors = meta.get("authors") or passage.source.value
        year = meta.get("year")
        year_str = f" ({year})" if year and year != 0 else ""
        doi_or_pmid = passage.doi_or_pmid or meta.get("doi_or_pmid")
        pmid_str = f" [{doi_or_pmid}]" if doi_or_pmid else ""
        url_str = f" Available at: {meta.get('url')}" if meta.get("url") else ""

        entry = (
            f"[{ref_idx}] {authors}{year_str}. {passage.title}. "
            f"Authority: {passage.source.value}.{pmid_str}{url_str}"
        )
        lines.append(entry)
        ref_idx += 1

    return "\n".join(lines)


def verify_citation_provenance(
    completion_text: str,
    valid_passages: list[RetrievedPassage],
) -> tuple[bool, list[str]]:
    """Verify that all citation markers in the response map to retrieved passages.

    Prevents hallucinated or fabricated citations (Rules.md §8 & PRD §6).

    Args:
        completion_text: Generated assistant completion text.
        valid_passages: Passages actually retrieved by the RAG engine.

    Returns:
        Tuple: (is_valid, list of ungrounded or invalid citation strings).
    """
    valid_labels: set[str] = {p.citation_label.strip("[]").lower() for p in valid_passages}
    valid_pmids: set[str] = {p.doi_or_pmid.lower() for p in valid_passages if p.doi_or_pmid}
    valid_indices: set[str] = {str(i) for i in range(1, len(valid_passages) + 1)}

    raw_matches = _CITATION_BRACKET_PATTERN.findall(completion_text)
    invalid_citations: list[str] = []

    for match in raw_matches:
        clean_match = match.strip().lower()

        # Check if match is a numeric index like [1], [2]
        if clean_match in valid_indices:
            continue

        # Check if match is a citation label like [NCCN Breast Screening v1.2024]
        if any(clean_match in label or label in clean_match for label in valid_labels):
            continue

        # Check if match contains valid PMID
        if any(pmid in clean_match for pmid in valid_pmids):
            continue

        # Ignore standard markdown footnotes or disclaimers
        if clean_match in ("context", "clinical context", "note"):
            continue

        invalid_citations.append(f"[{match}]")

    is_grounded = len(invalid_citations) == 0
    return is_grounded, invalid_citations


def format_grounded_response(
    response_text: str,
    passages: list[RetrievedPassage],
    append_bibliography: bool = True,
) -> str:
    """Attach formatted bibliography and citation provenance to response text.

    Args:
        response_text: The clinical response body.
        passages: The retrieved guideline passages.
        append_bibliography: Whether to append the bibliography block.

    Returns:
        Full response string containing citations.
    """
    if not append_bibliography or not passages:
        return response_text

    biblio = generate_bibliography(passages)
    return f"{response_text.rstrip()}\n{biblio}"
