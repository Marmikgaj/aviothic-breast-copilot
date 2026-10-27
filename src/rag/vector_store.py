"""Embedded ChromaDB vector store integration for oncology guidelines and literature.

Manages document indexing, dense vector search, and similarity scoring
per ADR-005 and Architecture §2.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from src.core.config import get_settings
from src.core.logging import get_logger
from src.rag.embeddings import BaseEmbeddingFunction, get_embedding_function
from src.rag.knowledge_base import get_default_guidelines
from src.rag.schemas import GuidelineDocument, GuidelineSource, RetrievedPassage

logger = get_logger(__name__)


class ChromaVectorStore:
    """Embedded ChromaDB vector store for oncology guideline retrieval.

    Supports persistent storage at `data/chromadb` and in-memory ephemeral
    mode for testing and isolated evaluations.
    """

    def __init__(
        self,
        persist_dir: Path | None = None,
        collection_name: str | None = None,
        embedding_fn: BaseEmbeddingFunction | None = None,
        is_ephemeral: bool = False,
    ) -> None:
        """Initialize ChromaDB client and collection.

        Args:
            persist_dir: Directory for persistent ChromaDB storage.
            collection_name: Name of the vector collection.
            embedding_fn: Custom embedding function (defaults to deterministic biomedical).
            is_ephemeral: If True, uses in-memory EphemeralClient (ideal for testing).
        """
        settings = get_settings()
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.rag_collection_name
        self.embedding_fn = embedding_fn or get_embedding_function()
        self.is_ephemeral = is_ephemeral

        self.client: ClientAPI
        if self.is_ephemeral:
            self.client = chromadb.EphemeralClient()
            logger.info("Initialized ephemeral ChromaDB client for RAG")
        else:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
            logger.info("Initialized persistent ChromaDB client", persist_dir=str(self.persist_dir))

        self.collection: Collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> Collection:
        """Get or create the ChromaDB collection."""
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents: list[GuidelineDocument]) -> int:
        """Embed and index clinical guideline documents into ChromaDB.

        Args:
            documents: List of GuidelineDocument objects to insert.

        Returns:
            Number of documents indexed.
        """
        if not documents:
            return 0

        ids: list[str] = [doc.id for doc in documents]
        texts: list[str] = [doc.text for doc in documents]
        embeddings: list[list[float]] = self.embedding_fn(texts)

        metadatas: list[dict[str, Any]] = []
        for doc in documents:
            meta: dict[str, Any] = {
                "title": doc.title,
                "source": doc.source.value,
                "citation_label": doc.citation_label,
                "year": doc.year or 0,
                "authors": doc.authors,
                "doi_or_pmid": doc.doi_or_pmid or "",
                "url": doc.url or "",
                "keywords": ", ".join(doc.keywords),
            }
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=cast(Any, embeddings),
            metadatas=cast(Any, metadatas),
        )

        logger.info("Indexed documents into ChromaDB", count=len(documents), collection=self.collection_name)
        return len(documents)

    def query(
        self,
        query: str,
        top_k: int = 3,
        sources: list[GuidelineSource] | None = None,
        min_similarity: float = 0.0,
    ) -> list[RetrievedPassage]:
        """Perform semantic search against indexed oncology guidelines.

        Args:
            query: Clinical query string.
            top_k: Maximum number of passages to return.
            sources: Optional source filters (e.g. [GuidelineSource.NCCN]).
            min_similarity: Minimum normalized similarity score threshold (0.0 to 1.0).

        Returns:
            Ranked list of RetrievedPassage objects.
        """
        start_time = time.perf_counter()
        query_embedding = self.embedding_fn.embed_query(query)

        where_filter: dict[str, Any] | None = None
        if sources:
            source_vals = [s.value for s in sources]
            if len(source_vals) == 1:
                where_filter = {"source": source_vals[0]}
            else:
                where_filter = {"source": {"$in": source_vals}}

        total_count = self.collection.count()
        if total_count == 0:
            return []

        n_results = min(top_k, total_count)
        results = self.collection.query(
            query_embeddings=cast(Any, [query_embedding]),
            n_results=n_results,
            where=where_filter,
            include=cast(Any, ["documents", "metadatas", "distances"]),
        )

        passages: list[RetrievedPassage] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return passages

        doc_ids = results["ids"][0]
        documents = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        for i, doc_id in enumerate(doc_ids):
            meta = metas[i] if i < len(metas) else {}
            text = documents[i] if i < len(documents) else ""
            dist = distances[i] if i < len(distances) else 1.0

            # Convert distance to normalized similarity score (0.0 to 1.0)
            # For cosine distance: dist in [0, 2], sim = max(0.0, 1.0 - dist)
            # For L2 distance: sim = 1.0 / (1.0 + dist)
            similarity = max(0.0, 1.0 - dist) if dist <= 2.0 else 1.0 / (1.0 + dist)
            similarity = min(1.0, round(similarity, 4))

            if similarity < min_similarity:
                continue

            src_str = str(meta.get("source", "NCCN"))
            try:
                source_enum = GuidelineSource(src_str)
            except ValueError:
                source_enum = GuidelineSource.NCCN

            passage = RetrievedPassage(
                id=doc_id,
                document_id=doc_id,
                text=text,
                score=similarity,
                citation_label=meta.get("citation_label", f"[{src_str}]"),
                source=source_enum,
                title=meta.get("title", ""),
                doi_or_pmid=meta.get("doi_or_pmid") or None,
                metadata=meta,
            )
            passages.append(passage)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            "Vector retrieval completed",
            query=query[:40],
            passages_found=len(passages),
            latency_ms=round(latency_ms, 2),
        )
        return passages

    def count(self) -> int:
        """Return the current document count in the collection."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete all records from the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self._get_or_create_collection()
        logger.info("ChromaDB collection reset", collection=self.collection_name)

    def seed_default_knowledge(self) -> int:
        """Populate the vector store with default curated guidelines.

        Returns:
            Number of default documents indexed.
        """
        guidelines = get_default_guidelines()
        return self.add_documents(guidelines)
