"""Stage 4 ORM contracts and opt-in Neon migration integration coverage."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


# The normal unit suite has no database dependency. Supplying this harmless URL
# allows importing SQLAlchemy model metadata without contacting a database.
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.models.entities import Diagnosis, KnowledgeDocument  # noqa: E402
from app.rag.config import EMBEDDING_DIMENSIONS, get_rag_settings  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def test_knowledge_document_has_canonical_rag_metadata_and_vector_column():
    document = KnowledgeDocument(
        misconception_id="LOOP-01",
        concept_id="C001",
        category="LOOPS",
        content="Trace the stop boundary before choosing an operator.",
        content_type="explanation",
        difficulty="beginner",
        stage="intervention",
        source="Stage 4 schema test",
        educational_purpose="practice boundary reasoning",
        rag_metadata={"evidence_basis": "literature"},
    )
    assert document.misconception_id == "LOOP-01"
    assert document.category == "LOOPS"
    assert document.stage == "intervention"
    assert document.rag_metadata == {"evidence_basis": "literature"}
    assert EMBEDDING_DIMENSIONS == get_rag_settings().embedding_dimensions == 384
    assert KnowledgeDocument.__table__.c.embedding.type.dim == EMBEDDING_DIMENSIONS
    assert {"category", "stage", "metadata", "embedding", "updated_at"} <= set(KnowledgeDocument.__table__.c.keys())


def test_diagnosis_supports_structured_reasoning_and_alternatives():
    diagnosis = Diagnosis(
        submission_id=1,
        is_correct=False,
        misconception_id="ARR-06",
        confidence=0.91,
        evidence=["The code accesses the first element with arr[1]."],
        reasoning="The response maps ordinal positions directly to indices.",
        alternative_misconceptions=["ARR-07"],
        error_type="conceptual",
        needs_intervention=True,
    )
    assert diagnosis.misconception_id == "ARR-06"
    assert diagnosis.evidence[0].startswith("The code")
    assert diagnosis.reasoning.startswith("The response")
    assert diagnosis.alternative_misconceptions == ["ARR-07"]


def test_existing_model_construction_remains_compatible_with_legacy_records():
    """New nullable/defaulted fields do not invalidate the pre-Stage-4 shape."""
    document = KnowledgeDocument(
        misconception_id="M001",
        concept_id="C001",
        content="Existing seed content remains valid.",
        content_type="explanation",
        difficulty="beginner",
        source="Existing seed",
        educational_purpose="legacy compatibility",
    )
    diagnosis = Diagnosis(
        submission_id=1,
        is_correct=False,
        misconception_id="M001",
        confidence=0.9,
        evidence=["Existing evidence."],
        error_type="conceptual",
        needs_intervention=True,
    )
    assert document.category is None
    assert document.embedding is None
    assert diagnosis.reasoning is None


@pytest.mark.skipif(
    not os.getenv("STAGE4_TEST_DATABASE_URL_UNPOOLED"),
    reason="Requires an isolated PostgreSQL/Neon test database via STAGE4_TEST_DATABASE_URL_UNPOOLED.",
)
def test_stage4_migration_creates_pgvector_schema_on_an_isolated_database():
    """Real integration test; intentionally opt-in to avoid touching shared Neon data."""
    env = os.environ | {"DATABASE_URL_UNPOOLED": os.environ["STAGE4_TEST_DATABASE_URL_UNPOOLED"]}
    subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=ROOT, env=env, check=True)

    from sqlalchemy import create_engine, text

    engine = create_engine(env["DATABASE_URL_UNPOOLED"])
    with engine.connect() as connection:
        assert connection.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")).scalar()
        columns = set(connection.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'knowledge_documents'")) .scalars())
        assert {"category", "stage", "metadata", "embedding", "updated_at"} <= columns
        assert connection.execute(text("SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid WHERE c.relname = 'knowledge_documents' AND a.attname = 'embedding'")) .scalar() == "vector(384)"
