"""Retrieval contracts for a future Neon Postgres + pgvector implementation."""

from typing import Protocol, Sequence

from app.rag.schemas import KnowledgeChunk, RetrievalQuery, RetrievalResult


class KnowledgeRetriever(Protocol):
    def retrieve(self, query: RetrievalQuery) -> Sequence[RetrievalResult]:
        """Return knowledge results for a misconception-scoped query."""
        ...


class PgvectorChunkStore(Protocol):
    """Persistence boundary; its implementation owns SQLAlchemy/pgvector SQL."""

    def similarity_search(self, query: RetrievalQuery, query_embedding: list[float]) -> Sequence[RetrievalResult]:
        """Search stored chunks using the query constraints and embedding."""
        ...

    def upsert(self, chunks: Sequence[KnowledgeChunk]) -> int:
        """Insert or update stored chunks and return the number written."""
        ...


class MisconceptionScopedRetriever:
    """Coordinates embedding and storage without permitting broad chat retrieval."""

    def __init__(self, embedder, store: PgvectorChunkStore) -> None:
        """Store the query embedder and chunk store used for retrieval."""
        self.embedder, self.store = embedder, store

    def retrieve(self, query: RetrievalQuery) -> Sequence[RetrievalResult]:
        """Embed the query text and delegate constrained search to the store."""
        embedding = self.embedder.embed_query(query.query_text)
        return self.store.similarity_search(query, embedding)
