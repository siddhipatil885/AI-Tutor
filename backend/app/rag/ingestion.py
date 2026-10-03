"""Interfaces for a later, deliberate ingestion command or admin workflow."""

from pathlib import Path
from typing import Protocol, Sequence

from app.rag.schemas import IngestionReport, KnowledgeChunk, KnowledgeDocumentInput


class KnowledgeDocumentLoader(Protocol):
    def load(self, source_root: Path) -> Sequence[KnowledgeDocumentInput]: ...


class Chunker(Protocol):
    def chunk(self, document: KnowledgeDocumentInput) -> Sequence[KnowledgeChunk]: ...


class KnowledgeChunkWriter(Protocol):
    def upsert(self, chunks: Sequence[KnowledgeChunk]) -> int: ...


class IngestionService:
    """Orchestration contract only; no startup ingestion or database writes yet."""

    def __init__(self, loader: KnowledgeDocumentLoader, chunker: Chunker, writer: KnowledgeChunkWriter) -> None:
        self.loader, self.chunker, self.writer = loader, chunker, writer

    def ingest(self, source_root: Path) -> IngestionReport:
        documents = self.loader.load(source_root)
        chunks = [chunk for document in documents for chunk in self.chunker.chunk(document)]
        written = self.writer.upsert(chunks)
        return IngestionReport(source_path=str(source_root), documents_seen=len(documents), chunks_created=len(chunks), chunks_upserted=written)
