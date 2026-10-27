"""Oncology RAG engine package providing vector indexing, retrieval, and citations."""

from src.rag.citation_engine import (
    format_grounded_response,
    generate_bibliography,
    verify_citation_provenance,
)
from src.rag.embeddings import (
    BaseEmbeddingFunction,
    DeterministicBiomedicalEmbeddingFunction,
    get_embedding_function,
)
from src.rag.knowledge_base import CURATED_ONCOLOGY_GUIDELINES, get_default_guidelines
from src.rag.retriever import OncologyRetriever
from src.rag.schemas import (
    GuidelineDocument,
    GuidelineSource,
    RetrievalQuery,
    RetrievalResult,
    RetrievedPassage,
)
from src.rag.vector_store import ChromaVectorStore

__all__ = [
    "CURATED_ONCOLOGY_GUIDELINES",
    "BaseEmbeddingFunction",
    "ChromaVectorStore",
    "DeterministicBiomedicalEmbeddingFunction",
    "GuidelineDocument",
    "GuidelineSource",
    "OncologyRetriever",
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievedPassage",
    "format_grounded_response",
    "generate_bibliography",
    "get_default_guidelines",
    "get_embedding_function",
    "verify_citation_provenance",
]
