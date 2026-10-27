"""High-level oncology retrieval service orchestrating vector search and citation grounding.

Provides grounded clinical context retrieval for chat, extraction summaries,
and report comparisons per PRD §4 and Architecture §1.
"""

from __future__ import annotations

import time

from src.api.schemas import ExtractedEntities
from src.core.config import get_settings
from src.core.logging import get_logger
from src.rag.citation_engine import format_grounded_response, generate_bibliography
from src.rag.schemas import RetrievalQuery, RetrievalResult
from src.rag.vector_store import ChromaVectorStore

logger = get_logger(__name__)


class OncologyRetriever:
    """Service providing grounded oncology literature retrieval and citation binding."""

    def __init__(self, vector_store: ChromaVectorStore | None = None) -> None:
        """Initialize the retriever with a ChromaVectorStore instance.

        Args:
            vector_store: Optional vector store instance (defaults to singleton persistent store).
        """
        self.vector_store = vector_store or ChromaVectorStore()
        # Ensure default knowledge base is seeded if collection is empty
        if self.vector_store.count() == 0:
            logger.info("Vector store empty, seeding default curated clinical knowledge base")
            self.vector_store.seed_default_knowledge()

    def retrieve(self, query: RetrievalQuery | str) -> RetrievalResult:
        """Retrieve top-k relevant clinical guideline passages for a query.

        Args:
            query: Either a query string or a RetrievalQuery object.

        Returns:
            RetrievalResult containing ranked passages, citations, and latency.
        """
        settings = get_settings()
        start_time = time.perf_counter()

        if isinstance(query, str):
            spec = RetrievalQuery(
                query=query,
                top_k=settings.rag_top_k,
                min_similarity=settings.rag_similarity_threshold,
            )
        else:
            spec = query

        passages = self.vector_store.query(
            query=spec.query,
            top_k=spec.top_k,
            sources=spec.sources,
            min_similarity=spec.min_similarity,
        )

        formatted_citations = generate_bibliography(passages)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return RetrievalResult(
            query=spec.query,
            passages=passages,
            formatted_citations=formatted_citations,
            latency_ms=round(latency_ms, 2),
        )

    def retrieve_for_entities(
        self,
        entities: ExtractedEntities,
        top_k: int = 3,
    ) -> RetrievalResult:
        """Automatically retrieve relevant clinical guidelines based on extracted entities.

        Constructs semantic queries targeting BI-RADS categories, TNM staging codes,
        and biomarker profiles identified in the patient's report.

        Args:
            entities: ExtractedEntities object from Phase 3 extraction pipeline.
            top_k: Number of total passages to return.

        Returns:
            RetrievalResult with deduplicated relevant guideline passages.
        """
        query_parts: list[str] = []

        if entities.birads:
            cats = [b.category for b in entities.birads]
            query_parts.append(f"BI-RADS Category {', '.join(cats)} management pathway and follow-up recommendation")

        if entities.tnm_staging:
            stages = [t.raw_stage for t in entities.tnm_staging]
            query_parts.append(f"AJCC breast cancer staging {', '.join(stages)}")

        if entities.biomarkers:
            markers = [f"{b.name} {b.status}" for b in entities.biomarkers]
            query_parts.append(f"Biomarker interpretation and guidelines {', '.join(markers)}")

        combined_query = "; ".join(query_parts) if query_parts else "breast cancer screening and staging guidelines"
        spec = RetrievalQuery(query=combined_query, top_k=top_k)
        return self.retrieve(spec)

    def ground_response(
        self,
        response_text: str,
        retrieved_result: RetrievalResult,
        append_bibliography: bool = True,
    ) -> str:
        """Ground a model response with retrieved passages and bibliography.

        Args:
            response_text: The generated clinical explanation.
            retrieved_result: The RetrievalResult containing evidence passages.
            append_bibliography: Whether to append the bibliography block.

        Returns:
            Full grounded response with references.
        """
        return format_grounded_response(
            response_text=response_text,
            passages=retrieved_result.passages,
            append_bibliography=append_bibliography,
        )
