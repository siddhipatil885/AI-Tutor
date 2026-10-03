from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base, Timestamped):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30), default="student")
    email: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)


class TeacherClass(Base, Timestamped):
    __tablename__ = "teacher_classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(40), default="python")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Enrollment(Base, Timestamped):
    __tablename__ = "class_enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("teacher_classes.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="active")


class Assignment(Base, Timestamped):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("teacher_classes.id"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(180))
    language: Mapped[str] = mapped_column(String(40), default="python")
    difficulty: Mapped[str] = mapped_column(String(30), default="beginner")
    question_count: Mapped[int] = mapped_column(Integer, default=1)
    question_types: Mapped[list] = mapped_column(JSON, default=list)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft")


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
    error_type: Mapped[str] = mapped_column(String(50))
    needs_intervention: Mapped[bool] = mapped_column(Boolean)


class KnowledgeDocument(Base, Timestamped):
    __tablename__ = "knowledge_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    misconception_id: Mapped[Optional[str]] = mapped_column(ForeignKey("misconceptions.id"), nullable=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(50))
    difficulty: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(180))
    educational_purpose: Mapped[str] = mapped_column(String(180))


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
