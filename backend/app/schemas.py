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


class TeacherClassCreate(BaseModel):
    teacher_id: int
    name: str
    language: str = "python"
    description: Optional[str] = None


class TeacherClassOut(BaseModel):
    id: int
    teacher_id: int
    name: str
    language: str
    description: Optional[str] = None


class EnrollmentOut(BaseModel):
    id: int
    class_id: int
    student_id: int
    status: str


class AssignmentOut(BaseModel):
    id: int
    class_id: int
    teacher_id: int
    title: str
    language: str
    difficulty: str
    question_count: int
    question_types: list[str]
    questions: list[dict]
    status: str


class StudentAssignmentOut(AssignmentOut):
    class_name: Optional[str] = None


class TeacherDashboardOut(BaseModel):
    total_students: int
    active_students: int
    average_assessment_performance: float
    average_mastery: float
    average_concept_mastery: float
    assignment_completion_rates: dict[str, float]
    weak_topics: list[dict]
    at_risk_students: list[dict]


class AssessmentDraftRequest(BaseModel):
    language: str = "python"
    topics: list[str] = Field(default_factory=lambda: ["loop boundaries"])
    difficulty: str = "beginner"
    question_count: int = 3
    question_types: list[str] = Field(default_factory=lambda: ["mcq", "output_prediction"])


class AssessmentQuestionOut(BaseModel):
    id: int
    language: str
    topic: str
    question_type: str
    difficulty: str
    prompt: str
    correct_answer: str
    explanation: str
    misconception_ids: list[str]


class AssessmentDraftOut(BaseModel):
    language: str
    difficulty: str
    questions: list[AssessmentQuestionOut]


class ProjectRecommendationOut(BaseModel):
    title: str
    language: str
    difficulty: str
    description: str
    focus: list[str]
    fit_score: float


class ProjectCatalogOut(BaseModel):
    language: str
    projects: list[ProjectRecommendationOut]
