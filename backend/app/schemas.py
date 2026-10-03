from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    concept_id: str = "C001"
    prompt: str
    expected_answer: str
    explanation: str
    difficulty: str = "beginner"


class QuestionOut(QuestionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question_kind: str


class SubmissionCreate(BaseModel):
    user_id: int = 1
    question_id: int
    answer: str = Field(min_length=1)
    reasoning: Optional[str] = None


class DiagnosisOut(BaseModel):
    id: Optional[int] = None
    is_correct: bool
    misconception_id: Optional[str] = None
    misconception_name: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    error_type: Literal["none", "conceptual", "procedural", "calculation", "syntax", "careless_input", "incomplete_reasoning", "uncertain"]
    needs_intervention: bool


class SubmissionOut(BaseModel):
    id: int
    diagnosis: DiagnosisOut


class InterventionOut(BaseModel):
    id: int
    diagnosis_id: int
    misconception_id: str
    title: str
    what_happened: str
    explanation: str
    worked_example: str
    guided_hint: str
    sources: list[str]


class ReassessmentCreate(BaseModel):
    user_id: int = 1
    assessment_id: Optional[int] = None
    intervention_id: int
    answer: Optional[str] = None


class ReassessmentOut(BaseModel):
    assessment_id: int
    question: QuestionOut
    status: Literal["pending", "unresolved", "improving", "resolved", "uncertain"]
    evidence: list[str]


class LearnerOut(BaseModel):
    user_id: int
    mastery: dict[str, float]
    active_misconceptions: list[str]
    resolved_misconceptions: list[str]
    trajectory: list[dict]


class ProgressOut(BaseModel):
    active_count: int
    resolved_count: int
    mastery: dict[str, float]
    trajectory: list[dict]
