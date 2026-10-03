"""Deterministic Stage 5 corpus validation, embedding, and persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import KnowledgeDocument
from app.rag.config import EMBEDDING_DIMENSIONS
from app.rag.schemas import IngestionReport, KnowledgeChunk, KnowledgeDocumentInput


class CorpusValidationError(ValueError):
    """Raised when curated corpus data violates the taxonomy contract."""


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per document, preserving input order."""
        ...


class KnowledgeDocumentLoader(Protocol):
    def load(self, source_root: Path) -> Sequence[KnowledgeDocumentInput]:
        """Return knowledge documents loaded from the given source root."""
        ...


class Chunker(Protocol):
    def chunk(self, document: KnowledgeDocumentInput) -> Sequence[KnowledgeChunk]:
        """Split a knowledge document into chunks for storage."""
        ...


class KnowledgeChunkWriter(Protocol):
    def upsert(self, chunks: Sequence[KnowledgeChunk]) -> int:
        """Insert or update chunks and return the number written."""
        ...


class KnowledgeCorpusLoader:
    """Loads one versioned JSON corpus and validates it against the taxonomy."""

    def load(self, corpus_path: Path, taxonomy_path: Path) -> list[KnowledgeDocumentInput]:
        try:
            corpus = json.loads(corpus_path.read_text())
            taxonomy = json.loads(taxonomy_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CorpusValidationError(f"Could not read RAG source files: {exc}") from exc

        taxonomy_records = taxonomy.get("misconceptions")
        if not isinstance(taxonomy_records, list):
            raise CorpusValidationError("Taxonomy must contain a misconceptions list.")
        taxonomy_by_id = {record.get("misconception_id"): record for record in taxonomy_records}
        documents = corpus.get("documents")
        if not isinstance(documents, list):
            raise CorpusValidationError("Corpus must contain a documents list.")

        validated: list[KnowledgeDocumentInput] = []
        seen_ids: set[str] = set()
        for index, raw in enumerate(documents):
            if not isinstance(raw, dict):
                raise CorpusValidationError(f"Document {index} must be an object.")
            misconception_id = raw.get("misconception_id")
            if misconception_id not in taxonomy_by_id:
                raise CorpusValidationError(f"Document {index} references unknown misconception_id {misconception_id!r}.")
            taxonomy_record = taxonomy_by_id[misconception_id]
            if raw.get("category") != taxonomy_record.get("category"):
                raise CorpusValidationError(f"Document {index} category does not match {misconception_id}.")
            document_id = raw.get("document_id")
            if document_id in seen_ids:
                raise CorpusValidationError(f"Duplicate document_id {document_id!r}.")
            seen_ids.add(document_id)
            try:
                metadata = dict(raw.get("metadata") or {})
                metadata.setdefault("topic", taxonomy_record["category"])
                metadata.setdefault("category", raw["category"])
                metadata.setdefault("concept_id", raw["concept_id"])
                metadata.setdefault("misconception_id", misconception_id)
                metadata.setdefault("content_type", raw["content_type"])
                metadata.setdefault("difficulty", raw["difficulty"])
                metadata.setdefault("stage", raw["stage"])
                metadata.setdefault("source", raw["source"])
                metadata.setdefault("educational_purpose", raw["educational_purpose"])
                payload = dict(raw)
                payload["metadata"] = metadata
                payload["source_path"] = str(corpus_path)
                validated.append(KnowledgeDocumentInput(**payload))
            except (KeyError, TypeError, ValueError) as exc:
                raise CorpusValidationError(f"Invalid document {index} ({document_id!r}): {exc}") from exc
        return validated


class KnowledgeDocumentWriter:
    """Upserts corpus rows using their stable misconception/type/source key."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, documents: Sequence[KnowledgeDocumentInput], embeddings: Sequence[list[float]]) -> tuple[int, int]:
        inserted = updated = 0
        for document, embedding in zip(documents, embeddings, strict=True):
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise CorpusValidationError(
                    f"{document.document_id} has {len(embedding)} embedding dimensions; expected {EMBEDDING_DIMENSIONS}."
                )
            existing = self.session.scalar(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.misconception_id == document.misconception_id,
                    KnowledgeDocument.content_type == document.content_type.value,
                    KnowledgeDocument.source == document.source,
                )
            )
            values = {
                "misconception_id": document.misconception_id,
                "category": document.category,
                "concept_id": document.concept_id,
                "content_type": document.content_type.value,
                "difficulty": document.difficulty.value,
                "stage": document.stage.value,
                "content": document.content,
                "source": document.source,
                "educational_purpose": document.educational_purpose,
                "rag_metadata": document.metadata.model_dump(mode="json") | {"document_id": document.document_id},
                "embedding": embedding,
            }
            if existing is None:
                self.session.add(KnowledgeDocument(**values))
                inserted += 1
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
                updated += 1
        self.session.flush()
        return inserted, updated


class IngestionService:
    """Compatibility orchestration contract for pre-Stage-5 callers."""

    def __init__(self, loader: KnowledgeDocumentLoader, chunker: Chunker, writer: KnowledgeChunkWriter) -> None:
        self.loader, self.chunker, self.writer = loader, chunker, writer

    def ingest(self, source_root: Path) -> IngestionReport:
        """Load, chunk, and upsert documents, returning counts for each stage."""
        documents = self.loader.load(source_root)
        chunks = [chunk for document in documents for chunk in self.chunker.chunk(document)]
        written = self.writer.upsert(chunks)
        return IngestionReport(
            source_path=str(source_root),
            documents_seen=len(documents),
            chunks_created=len(chunks),
            chunks_upserted=written,
        )


def ingest_corpus(
    session: Session,
    corpus_path: Path,
    taxonomy_path: Path,
    embedder: EmbeddingProvider,
) -> IngestionReport:
    documents = KnowledgeCorpusLoader().load(corpus_path, taxonomy_path)
    embeddings = embedder.embed_documents([document.content for document in documents])
    if len(embeddings) != len(documents):
        raise CorpusValidationError("Embedding provider returned a different number of vectors than documents.")
    for document, embedding in zip(documents, embeddings, strict=True):
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise CorpusValidationError(
                f"{document.document_id} has {len(embedding)} embedding dimensions; expected {EMBEDDING_DIMENSIONS}."
            )
    inserted, updated = KnowledgeDocumentWriter(session).upsert(documents, embeddings)
    return IngestionReport(
        source_path=str(corpus_path),
        documents_seen=len(documents),
        documents_validated=len(documents),
        embeddings_generated=len(embeddings),
        documents_inserted=inserted,
        documents_updated=updated,
    )
