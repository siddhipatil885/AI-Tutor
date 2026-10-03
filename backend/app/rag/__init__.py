"""Misconception-scoped retrieval contracts for Re:Learn.

This package deliberately exposes retrieval building blocks, not a generic
chat interface. Runtime ingestion and pgvector queries will be added later.
"""

from app.rag.schemas import RetrievalQuery, RetrievalResult

__all__ = ["RetrievalQuery", "RetrievalResult"]
