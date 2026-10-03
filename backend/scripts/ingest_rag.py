"""Ingest the curated Stage 5 RAG corpus into the configured PostgreSQL database."""

from pathlib import Path

from app.db.session import SessionLocal
from app.rag.embeddings import SentenceTransformerEmbedder
from app.rag.ingestion import ingest_corpus


ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "data" / "rag" / "knowledge" / "relearn_knowledge_corpus.json"
TAXONOMY_PATH = ROOT / "data" / "rag" / "taxonomy" / "relearn_taxonomy.json"


def main() -> None:
    with SessionLocal.begin() as session:
        report = ingest_corpus(session, CORPUS_PATH, TAXONOMY_PATH, SentenceTransformerEmbedder())
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
