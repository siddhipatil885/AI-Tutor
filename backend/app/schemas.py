from datetime import datetime
from typing import Any, Literal, Optional
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


class QuestionPromptOut(BaseModel):
    id: int
    concept_id: str
    prompt: str
    difficulty: str
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


class CodeSubmissionCreate(BaseModel):
    problem_id: str
    language: str = "python"
    function_name: str
    code: str = Field(min_length=1)
    tests: list[dict[str, Any]] = Field(default_factory=list)

class CodeDiagnosisCreate(BaseModel):
    problem_id: str = ""
    language: str = "python"
    code: str = Field(min_length=1)


class JudgeResultOut(BaseModel):
    passed: bool
    problem_id: str
    function_name: str
    failed_tests: list[dict[str, Any]]
    compiler_error: bool
    runtime_error: bool


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
    question: QuestionPromptOut
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


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)


class InstitutionOut(BaseModel):
    id: int
    name: str
    role: str
    member_count: int
    created_at: datetime


class InstitutionMemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    role: Literal["admin", "teacher", "student"]


class InstitutionMemberOut(BaseModel):
    user_id: int
    name: str
    email: Optional[str] = None
    role: str
    status: str


class InstitutionClassOut(BaseModel):
    id: int
    name: str
    language: str
    teacher_id: int


class InstitutionReportOut(BaseModel):
    member_count: int
    teacher_count: int
    student_count: int
    class_count: int
    published_assignment_count: int
    attempt_count: int
    average_score: Optional[float] = None


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


class AssignmentSubmissionCreate(BaseModel):
    answers: dict[str, str] = Field(min_length=1)


class AssignmentQuestionFeedback(BaseModel):
    question_id: int
    answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class AssignmentAttemptOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    attempt_number: int
    score: float
    answers: dict[str, str]
    feedback: list[AssignmentQuestionFeedback]
    created_at: datetime


class AssignmentReviewOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    student_name: str
    attempt_number: int
    score: float
    answers: dict[str, str]
    feedback: list[AssignmentQuestionFeedback]
    created_at: datetime


class LabCreate(BaseModel):
    teacher_id: int
    title: str
    language: str = "python"
    concept: str = "general"
    difficulty: str = "beginner"
    instructions: Optional[str] = None
    duration_minutes: int = 30


class LabOut(BaseModel):
    id: int
    teacher_id: int
    class_id: int
    title: str
    language: str
    concept: str
    difficulty: str
    instructions: Optional[str] = None
    duration_minutes: int
    status: str


class StudentLabOut(LabOut):
    class_name: Optional[str] = None


class LabSubmissionCreate(BaseModel):
    answer: str = Field(min_length=1)
    reflection: Optional[str] = None
    status: str = "submitted"


class LabSubmissionOut(BaseModel):
    id: int
    student_id: int
    lab_id: int
    answer: str
    reflection: Optional[str] = None
    status: str


class StudentAssignmentQuestionOut(BaseModel):
    id: int
    language: str
    topic: str
    question_type: str
    difficulty: str
    prompt: str


class StudentAssignmentOut(BaseModel):
    id: int
    class_id: int
    teacher_id: int
    title: str
    language: str
    difficulty: str
    question_count: int
    question_types: list[str]
    questions: list[StudentAssignmentQuestionOut]
    status: str
    class_name: Optional[str] = None


class TeacherDashboardOut(BaseModel):
    total_students: int
    active_students: int
    average_assessment_performance: Optional[float] = None
    average_mastery: Optional[float] = None
    average_concept_mastery: Optional[float] = None
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
