from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
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

class AuthIdentity(Base, Timestamped):
    __tablename__ = "auth_identities"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)


class Institution(Base, Timestamped):
    __tablename__ = "institutions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class InstitutionMembership(Base, Timestamped):
    __tablename__ = "institution_memberships"
    __table_args__ = (UniqueConstraint("institution_id", "user_id", name="uq_institution_user"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="active")


class InstitutionClass(Base, Timestamped):
    __tablename__ = "institution_classes"
    __table_args__ = (UniqueConstraint("institution_id", "class_id", name="uq_institution_class"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("teacher_classes.id"), index=True)


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


class AssignmentAttempt(Base, Timestamped):
    __tablename__ = "assignment_attempts"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", "attempt_number", name="uq_assignment_student_attempt"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(Float)
    feedback: Mapped[list] = mapped_column(JSON, default=list)


class Lab(Base, Timestamped):
    __tablename__ = "labs"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    class_id: Mapped[int] = mapped_column(ForeignKey("teacher_classes.id"))
    title: Mapped[str] = mapped_column(String(180))
    language: Mapped[str] = mapped_column(String(40), default="python")
    concept: Mapped[str] = mapped_column(String(80), default="general")
    difficulty: Mapped[str] = mapped_column(String(30), default="beginner")
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(30), default="draft")


class LabSubmission(Base, Timestamped):
    __tablename__ = "lab_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"))
    answer: Mapped[str] = mapped_column(Text)
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="submitted")


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
