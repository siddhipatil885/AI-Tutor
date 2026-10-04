"""Baseline Re:Learn application schema for fresh databases.

Existing installations created before Alembic must be stamped at this revision
before running the Stage 4 upgrade. Auth-owned tables are deliberately absent.
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_baseline_core_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("concepts", sa.Column("id", sa.String(length=40), primary_key=True), sa.Column("name", sa.String(length=160), nullable=False), sa.Column("description", sa.Text(), nullable=False))
    op.create_table("misconceptions", sa.Column("id", sa.String(length=40), nullable=False, primary_key=True), sa.Column("concept_id", sa.String(length=40), sa.ForeignKey("concepts.id"), nullable=False), sa.Column("name", sa.String(length=180), nullable=False), sa.Column("student_friendly_name", sa.String(length=180), nullable=False), sa.Column("description", sa.Text(), nullable=False))
    op.create_table("questions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("concept_id", sa.String(length=40), sa.ForeignKey("concepts.id"), nullable=False), sa.Column("prompt", sa.Text(), nullable=False), sa.Column("expected_answer", sa.Text(), nullable=False), sa.Column("explanation", sa.Text(), nullable=False), sa.Column("difficulty", sa.String(length=30), nullable=False, server_default="beginner"), sa.Column("question_kind", sa.String(length=30), nullable=False, server_default="initial"), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("submissions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False), sa.Column("answer", sa.Text(), nullable=False), sa.Column("reasoning", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("diagnoses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submissions.id"), nullable=False, unique=True), sa.Column("is_correct", sa.Boolean(), nullable=False), sa.Column("misconception_id", sa.String(length=40), sa.ForeignKey("misconceptions.id"), nullable=True), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("evidence", sa.JSON(), nullable=False), sa.Column("error_type", sa.String(length=50), nullable=False), sa.Column("needs_intervention", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("knowledge_documents", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("misconception_id", sa.String(length=40), sa.ForeignKey("misconceptions.id"), nullable=True), sa.Column("concept_id", sa.String(length=40), sa.ForeignKey("concepts.id"), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("content_type", sa.String(length=50), nullable=False), sa.Column("difficulty", sa.String(length=30), nullable=False), sa.Column("source", sa.String(length=180), nullable=False), sa.Column("educational_purpose", sa.String(length=180), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("interventions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("diagnosis_id", sa.Integer(), sa.ForeignKey("diagnoses.id"), nullable=False), sa.Column("content", sa.JSON(), nullable=False), sa.Column("retrieved_document_ids", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("assessments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("misconception_id", sa.String(length=40), sa.ForeignKey("misconceptions.id"), nullable=False), sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False), sa.Column("answer", sa.Text(), nullable=True), sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"), sa.Column("evidence", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("learner_profiles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True), sa.Column("mastery", sa.JSON(), nullable=False), sa.Column("active_misconceptions", sa.JSON(), nullable=False), sa.Column("resolved_misconceptions", sa.JSON(), nullable=False), sa.Column("trajectory", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))


def downgrade() -> None:
    op.drop_table("learner_profiles")
    op.drop_table("assessments")
    op.drop_table("interventions")
    op.drop_table("knowledge_documents")
    op.drop_table("diagnoses")
    op.drop_table("submissions")
    op.drop_table("questions")
    op.drop_table("misconceptions")
    op.drop_table("concepts")
    op.drop_table("users")
