"""Stage 5 corpus validation and deterministic ingestion tests."""

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.db.session import Base  # noqa: E402
from app.models.entities import KnowledgeDocument  # noqa: E402
from app.rag.ingestion import CorpusValidationError, KnowledgeCorpusLoader, ingest_corpus  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "data" / "rag" / "knowledge" / "relearn_knowledge_corpus.json"
TAXONOMY_PATH = ROOT / "data" / "rag" / "taxonomy" / "relearn_taxonomy.json"


class FakeEmbedder:
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] * self.dimensions for index, _ in enumerate(texts)]


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def test_corpus_covers_all_canonical_ids_with_controlled_content_types():
    documents = KnowledgeCorpusLoader().load(CORPUS_PATH, TAXONOMY_PATH)
    ids = {document.misconception_id for document in documents}
    content_types = {document.content_type.value for document in documents}
    assert len(ids) == 25
    assert len(documents) == 150
    assert content_types == {"explanation", "incorrect_reasoning", "correct_reasoning", "intervention", "hint", "practice"}


def test_unknown_misconception_id_fails(tmp_path: Path):
    corpus = json.loads(CORPUS_PATH.read_text())
    corpus["documents"][0]["misconception_id"] = "LOOP-99"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(corpus))
    with pytest.raises(CorpusValidationError, match="unknown misconception_id"):
        KnowledgeCorpusLoader().load(path, TAXONOMY_PATH)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("content_type", "not_allowed", "Input should be"),
        ("content", " ", "Content cannot be blank"),
    ],
)
def test_malformed_records_fail(tmp_path: Path, field: str, value: str, message: str):
    corpus = json.loads(CORPUS_PATH.read_text())
    corpus["documents"][0][field] = value
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(corpus))
    with pytest.raises(CorpusValidationError, match=message):
        KnowledgeCorpusLoader().load(path, TAXONOMY_PATH)


def test_embedding_dimension_is_checked_before_persistence(session: Session):
    with pytest.raises(CorpusValidationError, match="expected 384"):
        ingest_corpus(session, CORPUS_PATH, TAXONOMY_PATH, FakeEmbedder(dimensions=383))
    assert session.scalar(select(func.count()).select_from(KnowledgeDocument)) == 0


def test_ingestion_persists_metadata_and_is_idempotent(session: Session):
    first = ingest_corpus(session, CORPUS_PATH, TAXONOMY_PATH, FakeEmbedder())
    second = ingest_corpus(session, CORPUS_PATH, TAXONOMY_PATH, FakeEmbedder())
    session.commit()

    assert first.documents_inserted == 150
    assert first.documents_updated == 0
    assert second.documents_inserted == 0
    assert second.documents_updated == 150
    assert session.scalar(select(func.count()).select_from(KnowledgeDocument)) == 150
    document = session.scalar(select(KnowledgeDocument).where(KnowledgeDocument.misconception_id == "LOOP-01", KnowledgeDocument.content_type == "practice"))
    assert document is not None
    assert document.rag_metadata["document_id"] == "LOOP-01:practice"
    assert document.rag_metadata["evidence_source_ids"]
    assert document.source.startswith("Re:Learn taxonomy")
    assert len(document.embedding) == 384
