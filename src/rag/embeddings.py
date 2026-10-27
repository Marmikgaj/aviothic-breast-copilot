"""Biomedical embedding generators for vector retrieval.

Supports dense vector representation for clinical guidelines and PubMed literature
per ADR-005 and Architecture §2.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)

# Key oncology clinical vocabulary given elevated semantic weight in embeddings
_ONCOLOGY_ANCHOR_TERMS = {
    "birads": 3.0,
    "mammogram": 2.5,
    "ultrasound": 2.5,
    "mri": 2.5,
    "biopsy": 3.0,
    "tnm": 3.0,
    "stage": 2.5,
    "staging": 2.5,
    "tumor": 2.5,
    "ajcc": 3.0,
    "pt1": 3.0,
    "pt1a": 3.0,
    "pt1b": 3.0,
    "pt1c": 3.0,
    "pt2": 3.0,
    "pt3": 3.0,
    "pt4": 3.0,
    "t1": 3.0,
    "t1a": 3.0,
    "t1b": 3.0,
    "t1c": 3.0,
    "t2": 3.0,
    "t3": 3.0,
    "t4": 3.0,
    "pn0": 3.0,
    "pn1": 3.0,
    "pn1a": 3.0,
    "pn1mi": 3.0,
    "pn2": 3.0,
    "pn3": 3.0,
    "pm0": 3.0,
    "pm1": 3.0,
    "dcis": 3.0,
    "invasive": 2.5,
    "ductal": 2.5,
    "lobular": 2.5,
    "carcinoma": 2.5,
    "er": 3.0,
    "pr": 3.0,
    "her2": 3.5,
    "ki67": 3.0,
    "luminal": 2.5,
    "triple": 3.0,
    "negative": 2.5,
    "positive": 2.5,
    "equivocal": 2.5,
    "fish": 3.0,
    "ihc": 2.5,
    "sentinel": 2.5,
    "lymph": 2.5,
    "node": 2.0,
    "microcalcification": 2.5,
    "spiculated": 2.5,
    "asymmetry": 2.0,
    "followup": 2.0,
    "surveillance": 2.0,
    "excision": 2.0,
    "chemotherapy": 2.5,
    "endocrine": 2.5,
    "tamoxifen": 2.5,
    "trastuzumab": 3.0,
    "nccn": 3.0,
    "asco": 3.0,
    "cap": 2.5,
    "esmo": 2.5,
    "guideline": 2.0,
    "guidelines": 2.0,
    "category": 2.0,
}

_VECTOR_DIM = 384


class BaseEmbeddingFunction(ABC):
    """Abstract base class for embedding functions compatible with ChromaDB."""

    @abstractmethod
    def __call__(self, input: list[str]) -> list[list[float]]:
        """Embed a batch of document texts.

        Args:
            input: List of text strings.

        Returns:
            List of float embedding vectors.
        """
        ...

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string.

        Args:
            query: Query text.

        Returns:
            Float embedding vector.
        """
        ...


class DeterministicBiomedicalEmbeddingFunction(BaseEmbeddingFunction):
    """Deterministic dense biomedical embedding generator.

    Generates L2-normalized 384-dimensional dense vectors using weighted feature
    hashing across oncology anchor tokens, n-grams, and sub-words.
    Fast, completely offline, zero-network, and fully deterministic.
    """

    def __init__(self, dimension: int = _VECTOR_DIM) -> None:
        self.dimension = dimension

    def _embed_text(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        clean_text = text.lower()
        tokens = re.findall(r"\b[a-z0-9_+-]+\b", clean_text)

        if not tokens:
            return vec

        for token in tokens:
            weight = _ONCOLOGY_ANCHOR_TERMS.get(token, 1.0)
            # Hash token into vector dimensions using dual hash projections
            h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)  # noqa: S324
            h2 = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)

            idx1 = h1 % self.dimension
            idx2 = h2 % self.dimension

            sign1 = 1.0 if (h1 >> 8) & 1 else -1.0
            sign2 = 1.0 if (h2 >> 8) & 1 else -1.0

            vec[idx1] += sign1 * weight
            vec[idx2] += sign2 * weight * 0.5

        # Character trigrams for morphological robustness (e.g. 'her2' in 'her2-positive')
        for i in range(len(clean_text) - 2):
            trigram = clean_text[i : i + 3]
            h = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)  # noqa: S324
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[h % self.dimension] += sign * 0.2

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-12:
            vec = [x / norm for x in vec]

        return vec

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._embed_text(t) for t in input]

    def embed_query(self, query: str) -> list[float]:
        return self._embed_text(query)


class SentenceTransformerEmbeddingFunction(BaseEmbeddingFunction):
    """SentenceTransformers wrapper for bge-large-en or BioClinicalBERT."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self._model: Any = None

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                logger.warning(
                    "SentenceTransformers unavailable, falling back to deterministic biomedical embeddings",
                    error=str(exc),
                )
                self._model = DeterministicBiomedicalEmbeddingFunction()
        return self._model

    def __call__(self, input: list[str]) -> list[list[float]]:
        model = self._load_model()
        if isinstance(model, BaseEmbeddingFunction):
            return model(input)
        raw_embeds = model.encode(input, normalize_embeddings=True)
        return [list(map(float, vec)) for vec in raw_embeds]

    def embed_query(self, query: str) -> list[float]:
        model = self._load_model()
        if isinstance(model, BaseEmbeddingFunction):
            return model.embed_query(query)
        raw_embed = model.encode([query], normalize_embeddings=True)[0]
        return list(map(float, raw_embed))


def get_embedding_function(prefer_transformers: bool = False) -> BaseEmbeddingFunction:
    """Return appropriate embedding function based on configuration and environment.

    Args:
        prefer_transformers: Whether to attempt loading sentence-transformers.

    Returns:
        Instance of BaseEmbeddingFunction.
    """
    if prefer_transformers:
        try:
            import sentence_transformers  # noqa: F401

            return SentenceTransformerEmbeddingFunction()
        except ImportError:
            pass

    return DeterministicBiomedicalEmbeddingFunction()
