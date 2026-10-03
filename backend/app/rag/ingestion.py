"""Interfaces for a later, deliberate ingestion command or admin workflow."""

from pathlib import Path
from typing import Protocol, Sequence

from app.rag.schemas import IngestionReport, KnowledgeChunk, KnowledgeDocumentInput


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


class IngestionService:
    """Orchestration contract only; no startup ingestion or database writes yet."""

    def __init__(self, loader: KnowledgeDocumentLoader, chunker: Chunker, writer: KnowledgeChunkWriter) -> None:
        """Store the loader, chunker, and writer used by the ingestion workflow."""
        self.loader, self.chunker, self.writer = loader, chunker, writer

    def ingest(self, source_root: Path) -> IngestionReport:
        """Load, chunk, and upsert documents, returning counts for each stage."""
        documents = self.loader.load(source_root)
        chunks = [chunk for document in documents for chunk in self.chunker.chunk(document)]
        written = self.writer.upsert(chunks)
        return IngestionReport(source_path=str(source_root), documents_seen=len(documents), chunks_created=len(chunks), chunks_upserted=written)
