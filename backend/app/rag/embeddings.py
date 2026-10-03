"""Embedding boundary. Model loading is deferred until an implementation is used."""

from typing import Callable, Protocol, Sequence

from app.rag.config import EMBEDDING_DIMENSIONS, RagSettings, get_rag_settings


class EmbeddingDimensionError(ValueError):
    """Raised before persistence if a provider violates the schema contract."""


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per document, preserving input order."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Return an embedding vector for the query text."""
        ...


class SentenceTransformerEmbedder:
    """Lazy Sentence Transformers adapter; no download occurs at import time."""

    def __init__(self, settings: RagSettings | None = None, model_factory: Callable[[str], object] | None = None) -> None:
        """Store explicit or default settings without loading the model."""
        self.settings = settings or get_rag_settings()
        self.dimensions = self.settings.embedding_dimensions
        self._model = None
        self._model_factory = model_factory

    def _get_model(self):
        """Load the configured model on first use and reuse it thereafter."""
        if self._model is None:
            if self._model_factory:
                self._model = self._model_factory(self.settings.embedding_model)
            else:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.settings.embedding_model)
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Encode documents as normalized vectors in input order."""
        if not texts:
            return []
        vectors = self._get_model().encode(list(texts), normalize_embeddings=True)
        normalized = [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]
        for vector in normalized:
            if len(vector) != EMBEDDING_DIMENSIONS:
                raise EmbeddingDimensionError(
                    f"{self.settings.embedding_model} returned {len(vector)} dimensions; "
                    f"the KnowledgeDocument schema requires {EMBEDDING_DIMENSIONS}."
                )
        return normalized

    def embed_query(self, text: str) -> list[float]:
        """Encode query text as a normalized vector using the document model."""
        return self.embed_documents([text])[0]
