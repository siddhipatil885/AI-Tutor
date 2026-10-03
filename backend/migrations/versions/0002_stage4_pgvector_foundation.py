"""Add the non-destructive pgvector RAG foundation.

No embedding values, retrieval indexes, or application behavior are introduced.
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "0002_stage4_pgvector_foundation"
down_revision = "0001_baseline_core_schema"
branch_labels = None
depends_on = None

EMBEDDING_DIMENSIONS = 384  # Matches the locked all-MiniLM-L6-v2 schema contract.


def upgrade() -> None:
    # Explicit extension management belongs in the migration, not app startup.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("knowledge_documents", sa.Column("category", sa.String(length=50), nullable=True))
    op.add_column("knowledge_documents", sa.Column("stage", sa.String(length=30), nullable=False, server_default="intervention"))
    op.add_column("knowledge_documents", sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("knowledge_documents", sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True))
    op.add_column("knowledge_documents", sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")))
    op.execute("UPDATE knowledge_documents SET updated_at = created_at WHERE updated_at IS NULL")
    op.create_index("ix_knowledge_documents_misconception_stage_type_difficulty", "knowledge_documents", ["misconception_id", "stage", "content_type", "difficulty"])
    op.create_index("ix_knowledge_documents_category_concept", "knowledge_documents", ["category", "concept_id"])

    op.add_column("diagnoses", sa.Column("reasoning", sa.Text(), nullable=True))
    op.add_column("diagnoses", sa.Column("alternative_misconceptions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    op.drop_column("diagnoses", "alternative_misconceptions")
    op.drop_column("diagnoses", "reasoning")
    op.drop_index("ix_knowledge_documents_category_concept", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_misconception_stage_type_difficulty", table_name="knowledge_documents")
    op.drop_column("knowledge_documents", "updated_at")
    op.drop_column("knowledge_documents", "embedding")
    op.drop_column("knowledge_documents", "metadata")
    op.drop_column("knowledge_documents", "stage")
    op.drop_column("knowledge_documents", "category")
    # The extension is left installed: it may be used by another migration or
    # schema object, and dropping it during a downgrade could be destructive.
