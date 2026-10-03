from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.db.session import Base
from app.rag.config import EMBEDDING_DIMENSIONS, get_rag_settings


# Fail fast if a future configuration change diverges from this schema.
assert get_rag_settings().embedding_dimensions == EMBEDDING_DIMENSIONS


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base, Timestamped):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class Concept(Base):
    __tablename__ = "concepts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)


class Misconception(Base):
    __tablename__ = "misconceptions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    name: Mapped[str] = mapped_column(String(180))
    student_friendly_name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)


class Question(Base, Timestamped):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    prompt: Mapped[str] = mapped_column(Text)
    expected_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(30), default="beginner")
    question_kind: Mapped[str] = mapped_column(String(30), default="initial")


class Submission(Base, Timestamped):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    answer: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Diagnosis(Base, Timestamped):
    __tablename__ = "diagnoses"
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), unique=True)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    misconception_id: Mapped[Optional[str]] = mapped_column(ForeignKey("misconceptions.id"), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[list] = mapped_column(JSON)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternative_misconceptions: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    error_type: Mapped[str] = mapped_column(String(50))
    needs_intervention: Mapped[bool] = mapped_column(Boolean)


class KnowledgeDocument(Base, Timestamped):
    __tablename__ = "knowledge_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    misconception_id: Mapped[Optional[str]] = mapped_column(ForeignKey("misconceptions.id"), nullable=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    content: Mapped[str] = mapped_column(Text)
    # concept_id retains the project's established concept relationship.
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content_type: Mapped[str] = mapped_column(String(50))
    difficulty: Mapped[str] = mapped_column(String(30))
    stage: Mapped[str] = mapped_column(String(30), default="intervention", server_default="intervention")
    source: Mapped[str] = mapped_column(String(180))
    educational_purpose: Mapped[str] = mapped_column(String(180))
    # ``metadata`` is reserved by SQLAlchemy's declarative API, hence the
    # Python attribute is named rag_metadata while the persisted column is
    # precisely named metadata.
    rag_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, server_default="{}")
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_knowledge_documents_misconception_stage_type_difficulty", "misconception_id", "stage", "content_type", "difficulty"),
        Index("ix_knowledge_documents_category_concept", "category", "concept_id"),
    )


class Intervention(Base, Timestamped):
    __tablename__ = "interventions"
    id: Mapped[int] = mapped_column(primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id"))
    content: Mapped[dict] = mapped_column(JSON)
    retrieved_document_ids: Mapped[list] = mapped_column(JSON)


class Assessment(Base, Timestamped):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    misconception_id: Mapped[str] = mapped_column(ForeignKey("misconceptions.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    evidence: Mapped[list] = mapped_column(JSON, default=list)


class LearnerProfile(Base, Timestamped):
    __tablename__ = "learner_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    mastery: Mapped[dict] = mapped_column(JSON, default=dict)
    active_misconceptions: Mapped[list] = mapped_column(JSON, default=list)
    resolved_misconceptions: Mapped[list] = mapped_column(JSON, default=list)
    trajectory: Mapped[list] = mapped_column(JSON, default=list)
