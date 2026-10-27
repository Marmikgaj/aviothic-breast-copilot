"""Tests for Phase 5 RAG engine, ChromaDB vector store, embeddings, and citation engine."""

from __future__ import annotations

import math

import pytest

from src.api.schemas import BiomarkerEntity, BiradsEntity, ExtractedEntities, SourceSpan, TnmEntity
from src.rag.citation_engine import (
    format_grounded_response,
    generate_bibliography,
    verify_citation_provenance,
)
from src.rag.embeddings import DeterministicBiomedicalEmbeddingFunction
from src.rag.knowledge_base import CURATED_ONCOLOGY_GUIDELINES, get_default_guidelines
from src.rag.retriever import OncologyRetriever
from src.rag.schemas import GuidelineSource, RetrievedPassage
from src.rag.vector_store import ChromaVectorStore


class TestBiomedicalEmbeddings:
    """Test suite for deterministic biomedical embedding generation."""

    def test_embedding_dimension_and_norm(self) -> None:
        embed_fn = DeterministicBiomedicalEmbeddingFunction(dimension=384)
        vectors = embed_fn(["Invasive ductal carcinoma, ER positive, HER2 negative."])

        assert len(vectors) == 1
        vec = vectors[0]
        assert len(vec) == 384

        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-4

    def test_embedding_determinism(self) -> None:
        embed_fn = DeterministicBiomedicalEmbeddingFunction(dimension=384)
        text = "BI-RADS Category 4C: High suspicion for malignancy."

        vec1 = embed_fn.embed_query(text)
        vec2 = embed_fn.embed_query(text)
        assert vec1 == vec2

    def test_semantic_similarity_separation(self) -> None:
        embed_fn = DeterministicBiomedicalEmbeddingFunction(dimension=384)

        query = embed_fn.embed_query("HER2 gene amplification FISH testing")
        related = embed_fn.embed_query("ASCO CAP HER2 equivocal immunohistochemistry reflex FISH")
        unrelated = embed_fn.embed_query("Acute appendicitis surgical consultation emergency room")

        sim_related = sum(q * r for q, r in zip(query, related, strict=False))
        sim_unrelated = sum(q * u for q, u in zip(query, unrelated, strict=False))

        assert sim_related > sim_unrelated


class TestKnowledgeBase:
    """Test suite for curated clinical oncology knowledge base."""

    def test_default_guidelines_count_and_sources(self) -> None:
        docs = get_default_guidelines()
        assert len(docs) >= 6

        sources = {doc.source for doc in docs}
        assert GuidelineSource.NCCN in sources
        assert GuidelineSource.AJCC in sources
        assert GuidelineSource.ASCO_CAP in sources
        assert GuidelineSource.PUBMED in sources

    def test_guideline_document_integrity(self) -> None:
        for doc in CURATED_ONCOLOGY_GUIDELINES:
            assert doc.id
            assert len(doc.title) > 10
            assert len(doc.text) > 50
            assert doc.citation_label.startswith("[") and doc.citation_label.endswith("]")
            assert doc.doi_or_pmid is not None


class TestChromaVectorStore:
    """Test suite for ChromaVectorStore in ephemeral testing mode."""

    @pytest.fixture
    def vector_store(self) -> ChromaVectorStore:
        store = ChromaVectorStore(
            collection_name="test_oncology_guidelines",
            is_ephemeral=True,
        )
        store.seed_default_knowledge()
        return store

    def test_vector_store_seed_and_count(self, vector_store: ChromaVectorStore) -> None:
        count = vector_store.count()
        assert count == len(CURATED_ONCOLOGY_GUIDELINES)

    def test_query_birads_guidelines(self, vector_store: ChromaVectorStore) -> None:
        passages = vector_store.query("BI-RADS 4 biopsy recommendation", top_k=2)
        assert len(passages) >= 1
        assert passages[0].score >= 0.0
        assert passages[0].score <= 1.0

        nccn_found = any("NCCN" in p.source.value or "birads" in p.text.lower() for p in passages)
        assert nccn_found is True

    def test_query_her2_guidelines(self, vector_store: ChromaVectorStore) -> None:
        passages = vector_store.query("HER2 equivocal 2+ reflex FISH score", top_k=2)
        assert len(passages) >= 1
        labels = [p.citation_label for p in passages]
        assert any("HER2" in label for label in labels)

    def test_source_filtering(self, vector_store: ChromaVectorStore) -> None:
        nccn_only = vector_store.query(
            "breast cancer staging and management",
            top_k=5,
            sources=[GuidelineSource.NCCN],
        )
        for p in nccn_only:
            assert p.source == GuidelineSource.NCCN

    def test_reset_collection(self, vector_store: ChromaVectorStore) -> None:
        assert vector_store.count() > 0
        vector_store.reset()
        assert vector_store.count() == 0


class TestCitationEngine:
    """Test suite for citation formatting and provenance verification."""

    @pytest.fixture
    def sample_passages(self) -> list[RetrievedPassage]:
        return [
            RetrievedPassage(
                id="nccn_01",
                document_id="nccn_screening",
                text="BI-RADS 4 indicates suspicious finding requiring core needle biopsy.",
                score=0.92,
                citation_label="[NCCN Breast Screening v1.2024]",
                source=GuidelineSource.NCCN,
                title="NCCN Breast Cancer Screening Guidelines",
                doi_or_pmid="NCCN-BC-2024",
                metadata={"authors": "Gradishar WJ, et al.", "year": 2024},
            ),
            RetrievedPassage(
                id="asco_01",
                document_id="asco_her2",
                text="HER2 2+ requires reflex FISH testing.",
                score=0.88,
                citation_label="[ASCO/CAP HER2 Update 2023]",
                source=GuidelineSource.ASCO_CAP,
                title="HER2 Testing in Breast Cancer",
                doi_or_pmid="PMID: 30412397",
                metadata={"authors": "Wolff AC, et al.", "year": 2023},
            ),
        ]

    def test_generate_bibliography(self, sample_passages: list[RetrievedPassage]) -> None:
        biblio = generate_bibliography(sample_passages)
        assert "Clinical References & Guideline Citations" in biblio
        assert "[1] Gradishar WJ, et al. (2024)" in biblio
        assert "[2] Wolff AC, et al. (2023)" in biblio
        assert "PMID: 30412397" in biblio

    def test_verify_citation_provenance_valid(self, sample_passages: list[RetrievedPassage]) -> None:
        valid_text = (
            "Per clinical guidelines, a biopsy is recommended for suspicious lesions [1]. "
            "Reflex FISH testing is mandatory for equivocal cases [ASCO/CAP HER2 Update 2023]."
        )
        is_grounded, invalid = verify_citation_provenance(valid_text, sample_passages)
        assert is_grounded is True
        assert len(invalid) == 0

    def test_verify_citation_provenance_detects_hallucinations(
        self,
        sample_passages: list[RetrievedPassage],
    ) -> None:
        hallucinated_text = (
            "This was proven in recent studies [99] and confirmed by Smith et al. [Fabricated Guideline 2099]."
        )
        is_grounded, invalid = verify_citation_provenance(hallucinated_text, sample_passages)
        assert is_grounded is False
        assert "[99]" in invalid
        assert "[Fabricated Guideline 2099]" in invalid

    def test_format_grounded_response(self, sample_passages: list[RetrievedPassage]) -> None:
        response = "Core needle biopsy is indicated for BI-RADS 4 findings [1]."
        grounded = format_grounded_response(response, sample_passages)
        assert response in grounded
        assert "Clinical References" in grounded


class TestOncologyRetriever:
    """Test suite for high-level OncologyRetriever service."""

    @pytest.fixture
    def retriever(self) -> OncologyRetriever:
        store = ChromaVectorStore(
            collection_name="test_retriever_collection",
            is_ephemeral=True,
        )
        return OncologyRetriever(vector_store=store)

    def test_retrieve_query_string(self, retriever: OncologyRetriever) -> None:
        result = retriever.retrieve("What is the follow-up for BI-RADS Category 3?")
        assert len(result.passages) > 0
        assert result.latency_ms >= 0.0
        assert "Clinical References" in result.formatted_citations

    def test_retrieve_for_entities(self, retriever: OncologyRetriever) -> None:
        span = SourceSpan(start_char=0, end_char=10, snippet="snippet")
        entities = ExtractedEntities(
            birads=[BiradsEntity(category="4C", descriptor="High Suspicion", span=span, confidence=0.95)],
            tnm_staging=[TnmEntity(raw_stage="pT2 pN1a M0", span=span, confidence=0.90)],
            biomarkers=[BiomarkerEntity(name="HER2", status="equivocal", ihc_score="2+", span=span, confidence=0.92)],
        )

        result = retriever.retrieve_for_entities(entities, top_k=3)
        assert len(result.passages) >= 1
        assert len(result.formatted_citations) > 0

    def test_to_context_string_formatting(self, retriever: OncologyRetriever) -> None:
        result = retriever.retrieve("AJCC tumor staging pT1c")
        context_str = result.to_context_string()

        assert "Passage [1]" in context_str
        assert "AJCC" in context_str or "Staging" in context_str
