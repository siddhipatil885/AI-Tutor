"""Embedding boundary. Model loading is deferred until an implementation is used."""

from typing import Protocol, Sequence

from app.rag.config import RagSettings, get_rag_settings


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Lazy Sentence Transformers adapter; no download occurs at import time."""

    def __init__(self, settings: RagSettings | None = None) -> None:
        self.settings = settings or get_rag_settings()
        self.dimensions = self.settings.embedding_dimensions
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.settings.embedding_model)
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._get_model().encode(list(texts), normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
