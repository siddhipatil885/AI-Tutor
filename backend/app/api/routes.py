from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Assessment, Assignment, AssignmentAttempt, Diagnosis, Enrollment, Institution, InstitutionClass, InstitutionMembership, Intervention, Lab, LearnerProfile, Question, Submission, TeacherClass, User
from app.schemas import (AssessmentDraftOut, AssessmentDraftRequest, AssignmentAttemptOut, AssignmentOut, AssignmentReviewOut, AssignmentSubmissionCreate, DiagnosisOut, EnrollmentOut, InstitutionClassOut, InstitutionCreate, InstitutionMemberCreate, InstitutionMemberOut, InstitutionOut, InstitutionReportOut, InterventionOut, LabCreate, LabOut, LabSubmissionCreate, LabSubmissionOut, LearnerOut, ProgressOut, ProjectCatalogOut, ProjectRecommendationOut, QuestionCreate, QuestionOut, QuestionPromptOut, ReassessmentCreate, ReassessmentOut, StudentAssignmentOut, StudentLabOut, SubmissionCreate, SubmissionOut, TeacherClassCreate, TeacherClassOut, TeacherDashboardOut)
from app.services.assessment import create_assignment, generate_assessment
from app.services.auth import get_current_user_from_headers, require_role
from app.services.diagnosis import diagnose, normalize
from app.services.intervention import create_intervention
from app.services.learner import apply_assessment, profile_for
from app.services.projects import PROJECT_CATALOG, recommend_projects
from app.services.teacher import build_teacher_dashboard, create_class, create_lab, enroll_student, list_classes, list_class_assignments, list_labs, list_student_assignments, list_student_labs, submit_lab_progress, update_lab_status

router = APIRouter(prefix="/api")


def require_user_id(requested_id: int, current_user: dict) -> None:
    if current_user["role"] != "admin" and requested_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="You cannot access another user's data.")


def require_class_access(class_id: int, current_user: dict, db: Session) -> TeacherClass:
    class_record = db.get(TeacherClass, class_id)
    if class_record is None:
        raise HTTPException(status_code=404, detail="Class not found")
    if current_user["role"] == "admin" or class_record.teacher_id == current_user["id"]:
        return class_record
    enrollment = db.query(Enrollment).filter_by(class_id=class_id, student_id=current_user["id"], status="active").one_or_none()
    if enrollment is None:
        raise HTTPException(status_code=403, detail="You are not a member of this class.")
    return class_record


def require_institution_role(institution_id: int, current_user: dict, db: Session, allowed_roles: set[str] | None = None) -> str:
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    if current_user["role"] == "admin":
        return "admin"
    membership = db.query(InstitutionMembership).filter_by(
        institution_id=institution_id,
        user_id=current_user["id"],
        status="active",
    ).one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="You are not a member of this institution.")
    if allowed_roles and membership.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Your institution role does not allow this action.")
    return membership.role


@router.get("/auth/me")
def auth_session(current_user: dict = Depends(get_current_user_from_headers)):
    return current_user


def question_out(q: Question) -> QuestionOut:
    return QuestionOut(id=q.id, concept_id=q.concept_id, prompt=q.prompt, expected_answer=q.expected_answer, explanation=q.explanation, difficulty=q.difficulty, question_kind=q.question_kind)


def diagnosis_out(d: Diagnosis) -> DiagnosisOut:
    name = "Loop boundary / off-by-one" if d.misconception_id == "M001" else None
    return DiagnosisOut(id=d.id, is_correct=d.is_correct, misconception_id=d.misconception_id, misconception_name=name, confidence=d.confidence, evidence=d.evidence, error_type=d.error_type, needs_intervention=d.needs_intervention)


@router.get("/questions/default", response_model=QuestionPromptOut)
def default_question(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    question = db.query(Question).filter_by(question_kind="initial").first()
    if not question: raise HTTPException(404, "No demo question available")
    return QuestionPromptOut(id=question.id, concept_id=question.concept_id, prompt=question.prompt, difficulty=question.difficulty, question_kind=question.question_kind)


@router.post("/questions", response_model=QuestionOut, status_code=201)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    q = Question(**payload.model_dump())
    db.add(q); db.commit(); db.refresh(q)
    return question_out(q)


@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    q = db.get(Question, question_id)
    if not q: raise HTTPException(404, "Question not found")
    return question_out(q)


@router.post("/submissions", response_model=SubmissionOut, status_code=201)
def submit(payload: SubmissionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    q = db.get(Question, payload.question_id)
    if not q: raise HTTPException(404, "Question not found")
    record = Submission(user_id=current_user["id"], question_id=payload.question_id, answer=payload.answer, reasoning=payload.reasoning)
    db.add(record); db.flush()
    result = diagnose(q.expected_answer, payload.answer, payload.reasoning)
    diagnosis = Diagnosis(submission_id=record.id, is_correct=result.is_correct, misconception_id=result.misconception_id, confidence=result.confidence, evidence=result.evidence, error_type=result.error_type, needs_intervention=result.needs_intervention)
    db.add(diagnosis); db.commit(); db.refresh(diagnosis)
    if result.misconception_id:
        profile = profile_for(db, current_user["id"])
        active = list(profile.active_misconceptions or [])
        if result.misconception_id not in active: active.append(result.misconception_id)
        profile.active_misconceptions = active; db.commit()
    return SubmissionOut(id=record.id, diagnosis=diagnosis_out(diagnosis))


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    submission = db.get(Submission, submission_id)
    if not submission: raise HTTPException(404, "Submission not found")
    require_user_id(submission.user_id, current_user)
    d = db.query(Diagnosis).filter_by(submission_id=submission_id).first()
    return SubmissionOut(id=submission.id, diagnosis=diagnosis_out(d))


@router.post("/diagnose", response_model=DiagnosisOut)
def direct_diagnose(payload: SubmissionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    q = db.get(Question, payload.question_id)
    if not q: raise HTTPException(404, "Question not found")
    return diagnose(q.expected_answer, payload.answer, payload.reasoning)


@router.post("/interventions", response_model=InterventionOut, status_code=201)
def intervention(submission_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    d = db.query(Diagnosis).filter_by(submission_id=submission_id).first()
    submission = db.get(Submission, submission_id)
    if not d or not submission: raise HTTPException(404, "Submission or diagnosis not found")
    require_user_id(submission.user_id, current_user)
    if not d.needs_intervention: raise HTTPException(422, "This diagnosis does not justify a targeted intervention.")
    return create_intervention(db, d, db.get(Question, submission.question_id))


@router.post("/reassessment", response_model=ReassessmentOut)
def reassess(payload: ReassessmentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    intervention = db.get(Intervention, payload.intervention_id)
    if not intervention: raise HTTPException(404, "Intervention not found")
    diagnosis = db.get(Diagnosis, intervention.diagnosis_id)
    if not diagnosis or not diagnosis.misconception_id: raise HTTPException(422, "No misconception available for reassessment")
    original_submission = db.get(Submission, diagnosis.submission_id)
    require_user_id(original_submission.user_id, current_user)
    assessment = db.get(Assessment, payload.assessment_id) if payload.assessment_id else None
    if assessment and assessment.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="You cannot access another user's reassessment.")
    if not assessment:
        follow_up = Question(concept_id="C001", prompt="A different loop: What values are printed by `for n in range(3, 7): print(n)`?", expected_answer="3 4 5 6", explanation="The start is included; the stop value 7 is excluded.", difficulty="beginner", question_kind="reassessment")
        db.add(follow_up); db.flush()
        assessment = Assessment(user_id=current_user["id"], misconception_id=diagnosis.misconception_id, question_id=follow_up.id, status="pending", evidence=[])
        db.add(assessment); db.commit(); db.refresh(assessment)
        return ReassessmentOut(assessment_id=assessment.id, question=question_out(follow_up), status="pending", evidence=["This follow-up changes the numbers while testing the same exclusive-stop idea."])
    question = db.get(Question, assessment.question_id)
    if payload.answer is None: raise HTTPException(422, "Submit an answer for this reassessment.")
    correct = normalize(payload.answer) == normalize(question.expected_answer)
    evidence = ["The follow-up answer uses the exclusive stop boundary correctly."] if correct else ["The follow-up answer still includes or omits a boundary value."]
    profile = profile_for(db, current_user["id"])
    status = apply_assessment(db, profile, assessment.misconception_id, correct, evidence)
    assessment.answer, assessment.status, assessment.evidence = payload.answer, status, evidence
    db.commit()
    return ReassessmentOut(assessment_id=assessment.id, question=question_out(question), status=status, evidence=evidence)


@router.get("/learner/{user_id}", response_model=LearnerOut)
def learner(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(user_id, current_user)
    p = profile_for(db, user_id)
    return LearnerOut(user_id=user_id, mastery=p.mastery, active_misconceptions=p.active_misconceptions, resolved_misconceptions=p.resolved_misconceptions, trajectory=p.trajectory)


@router.get("/learner/{user_id}/misconceptions")
def misconceptions(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(user_id, current_user)
    p = profile_for(db, user_id)
    return {"active": p.active_misconceptions, "resolved": p.resolved_misconceptions}


@router.get("/learner/{user_id}/progress", response_model=ProgressOut)
def progress(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(user_id, current_user)
    p = profile_for(db, user_id)
    return ProgressOut(active_count=len(p.active_misconceptions), resolved_count=len(p.resolved_misconceptions), mastery=p.mastery, trajectory=p.trajectory)


@router.get("/teacher/dashboard", response_model=TeacherDashboardOut)
def teacher_dashboard(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    class_ids = [row.id for row in db.query(TeacherClass.id).filter_by(teacher_id=current_user["id"]).all()]
    if not class_ids:
        return build_teacher_dashboard([])
    student_ids = sorted({row.student_id for row in db.query(Enrollment.student_id).filter(
        Enrollment.class_id.in_(class_ids), Enrollment.status == "active").all()})
    if not student_ids:
        return build_teacher_dashboard([])
    users = {user.id: user for user in db.query(User).filter(User.id.in_(student_ids)).all()}
    profiles = {profile.user_id: profile for profile in db.query(LearnerProfile).filter(LearnerProfile.user_id.in_(student_ids)).all()}
    outcomes: dict[int, list[bool]] = {}
    records = (db.query(Submission.user_id, Diagnosis.is_correct)
        .join(Diagnosis, Diagnosis.submission_id == Submission.id)
        .filter(Submission.user_id.in_(student_ids))
        .all())
    for user_id, is_correct in records:
        outcomes.setdefault(user_id, []).append(is_correct)
    students = [{
        "name": users[user_id].name,
        "mastery": profiles[user_id].mastery if user_id in profiles else {},
        "active_misconceptions": profiles[user_id].active_misconceptions if user_id in profiles else [],
        "has_submission": bool(outcomes.get(user_id)),
        "assessment_performance": (sum(outcomes[user_id]) / len(outcomes[user_id]) * 100) if outcomes.get(user_id) else None,
    } for user_id in student_ids if user_id in users]
    return build_teacher_dashboard(students)


@router.get("/classes/{class_id}/labs", response_model=list[LabOut])
def class_labs(class_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_class_access(class_id, current_user, db)
    return list_labs(class_id=class_id, db=db)


@router.get("/students/{student_id}/labs", response_model=list[StudentLabOut])
def student_labs(student_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(student_id, current_user)
    return list_student_labs(student_id=student_id, db=db)


@router.post("/students/{student_id}/labs/{lab_id}/submit", response_model=LabSubmissionOut, status_code=201)
def submit_student_lab(student_id: int, lab_id: int, payload: LabSubmissionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(student_id, current_user)
    return submit_lab_progress(lab_id=lab_id, student_id=student_id, answer=payload.answer, reflection=payload.reflection, status=payload.status, db=db)


@router.post("/teacher/classes/{class_id}/labs", response_model=LabOut, status_code=201)
def teacher_lab_create(class_id: int, payload: LabCreate, db: Session = Depends(get_db), current_user: dict | None = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    class_record = require_class_access(class_id, current_user, db)
    return create_lab(
        teacher_id=class_record.teacher_id,
        class_id=class_id,
        title=payload.title,
        language=payload.language,
        concept=payload.concept,
        difficulty=payload.difficulty,
        instructions=payload.instructions,
        duration_minutes=payload.duration_minutes,
        db=db,
    )


@router.post("/labs/{lab_id}/status", response_model=LabOut)
def lab_status_update(lab_id: int, status: str, db: Session = Depends(get_db), current_user: dict | None = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    lab = db.get(Lab, lab_id)
    if lab is None: raise HTTPException(status_code=404, detail="Lab not found")
    if current_user["role"] != "admin" and lab.teacher_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="You do not manage this lab.")
    return update_lab_status(lab_id=lab_id, status=status, db=db)


@router.get("/classes/{class_id}/assignments", response_model=list[AssignmentOut])
def class_assignments(class_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    require_class_access(class_id, current_user, db)
    return list_class_assignments(class_id=class_id, db=db)


@router.get("/students/{student_id}/assignments", response_model=list[StudentAssignmentOut])
def student_assignments(student_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(student_id, current_user)
    return [item for item in list_student_assignments(student_id=student_id, db=db) if item["status"] == "published"]


@router.get("/student/assignments", response_model=list[StudentAssignmentOut])
def learner_assignments(student_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(student_id, current_user)
    return [item for item in list_student_assignments(student_id=student_id, db=db) if item["status"] == "published"]


@router.get("/teacher/classes/{class_id}/assignments", response_model=list[AssignmentOut])
def teacher_class_assignments(class_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    require_class_access(class_id, current_user, db)
    return list_class_assignments(class_id=class_id, db=db)


@router.post("/teacher/classes", response_model=TeacherClassOut, status_code=201)
def teacher_class_create(payload: TeacherClassCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    return create_class(current_user["id"], payload.name, payload.language, payload.description, db=db)


@router.get("/teacher/classes", response_model=list[TeacherClassOut])
def teacher_classes(teacher_id: int | None = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    scoped_teacher_id = teacher_id if current_user["role"] == "admin" else current_user["id"]
    return list_classes(teacher_id=scoped_teacher_id, db=db)


@router.post("/teacher/classes/{class_id}/enroll", response_model=EnrollmentOut, status_code=201)
def teacher_class_enroll(class_id: int, student_id: int = 0, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    require_class_access(class_id, current_user, db)
    if student_id <= 0:
        raise HTTPException(422, "A valid student_id is required.")
    return enroll_student(class_id=class_id, student_id=student_id, db=db)


@router.post("/teacher/assessments", response_model=AssignmentOut, status_code=201)
def teacher_assignment_create(class_id: int, teacher_id: int, title: str, language: str = "python", difficulty: str = "beginner", question_count: int = 2, question_types: str | None = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    class_record = require_class_access(class_id, current_user, db)
    question_list = [item.strip() for item in (question_types or "mcq,output_prediction").split(",") if item.strip()]
    return create_assignment(
        teacher_id=class_record.teacher_id,
        class_id=class_id,
        title=title,
        language=language,
        difficulty=difficulty,
        question_count=question_count,
        question_types=question_list,
        db=db,
    )


@router.post("/teacher/assignments/{assignment_id}/publish", response_model=AssignmentOut)
def publish_assignment(assignment_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    require_class_access(assignment.class_id, current_user, db)
    if assignment.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft assignments can be published.")
    assignment.status = "published"
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/submissions", response_model=AssignmentAttemptOut, status_code=201)
def submit_assignment(assignment_id: int, payload: AssignmentSubmissionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["student"], current_user)
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.status != "published":
        raise HTTPException(status_code=404, detail="Published assignment not found")
    require_class_access(assignment.class_id, current_user, db)

    questions = assignment.questions or []
    question_ids = {str(question["id"]) for question in questions}
    if set(payload.answers) != question_ids:
        raise HTTPException(status_code=422, detail="Provide exactly one answer for each assignment question.")
    if any(not answer.strip() for answer in payload.answers.values()):
        raise HTTPException(status_code=422, detail="Answers cannot be blank.")

    feedback = []
    correct_count = 0
    for question in questions:
        question_id = str(question["id"])
        answer = payload.answers[question_id].strip()
        correct_answer = str(question.get("correct_answer") or "")
        is_correct = normalize(answer) == normalize(correct_answer)
        correct_count += int(is_correct)
        feedback.append({
            "question_id": question["id"],
            "answer": answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": str(question.get("explanation") or "No explanation is available."),
        })

    previous_attempt = db.query(func.max(AssignmentAttempt.attempt_number)).filter_by(
        assignment_id=assignment.id,
        student_id=current_user["id"],
    ).scalar()
    attempt = AssignmentAttempt(
        assignment_id=assignment.id,
        student_id=current_user["id"],
        attempt_number=(previous_attempt or 0) + 1,
        answers=payload.answers,
        score=(correct_count / len(questions) * 100) if questions else 0,
        feedback=feedback,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/teacher/assignments/{assignment_id}/submissions", response_model=list[AssignmentReviewOut])
def review_assignment_submissions(assignment_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    require_class_access(assignment.class_id, current_user, db)
    attempts = (db.query(AssignmentAttempt, User.name)
        .join(User, User.id == AssignmentAttempt.student_id)
        .filter(AssignmentAttempt.assignment_id == assignment_id)
        .order_by(AssignmentAttempt.student_id, AssignmentAttempt.attempt_number)
        .all())
    return [{
        "id": attempt.id,
        "assignment_id": attempt.assignment_id,
        "student_id": attempt.student_id,
        "student_name": name,
        "attempt_number": attempt.attempt_number,
        "score": attempt.score,
        "answers": attempt.answers,
        "feedback": attempt.feedback,
        "created_at": attempt.created_at,
    } for attempt, name in attempts]


@router.get("/students/{student_id}/assignments/{assignment_id}/attempts", response_model=list[AssignmentAttemptOut])
def student_assignment_attempts(student_id: int, assignment_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_user_id(student_id, current_user)
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.status != "published":
        raise HTTPException(status_code=404, detail="Published assignment not found")
    require_class_access(assignment.class_id, current_user, db)
    return (db.query(AssignmentAttempt)
        .filter_by(assignment_id=assignment_id, student_id=current_user["id"])
        .order_by(AssignmentAttempt.attempt_number)
        .all())


@router.post("/teacher/assessments/generate", response_model=AssessmentDraftOut)
def generate_teacher_assessment(payload: AssessmentDraftRequest, current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["teacher", "admin"], current_user)
    generated = generate_assessment(
        language=payload.language,
        topics=payload.topics,
        difficulty=payload.difficulty,
        question_count=payload.question_count,
        question_types=payload.question_types,
    )
    return AssessmentDraftOut(**generated)


@router.get("/projects", response_model=ProjectCatalogOut)
def project_catalog(language: str = "python"):
    language_key = (language or "python").lower()
    catalog = PROJECT_CATALOG.get(language_key, PROJECT_CATALOG["python"])
    projects = [{
        "title": item["title"],
        "language": language_key,
        "difficulty": item["difficulty"],
        "description": item["description"],
        "focus": item["focus"],
        "fit_score": round(0.75, 3),
    } for item in catalog]
    return {"language": language_key, "projects": projects}


@router.post("/projects/recommend", response_model=list[ProjectRecommendationOut])
def project_recommendations(payload: dict):
    language = str(payload.get("language", "python")).lower()
    mastery = payload.get("mastery", {}) or {}
    completed = payload.get("completed_projects") or []
    return recommend_projects(language=language, mastery=mastery, completed_projects=completed)


@router.get("/institutions", response_model=list[InstitutionOut])
def institutions(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    if current_user["role"] == "admin":
        records = db.query(Institution).order_by(Institution.name).all()
        roles = {record.id: "admin" for record in records}
    else:
        rows = (db.query(Institution, InstitutionMembership.role)
            .join(InstitutionMembership, InstitutionMembership.institution_id == Institution.id)
            .filter(InstitutionMembership.user_id == current_user["id"], InstitutionMembership.status == "active")
            .order_by(Institution.name)
            .all())
        records = [record for record, _role in rows]
        roles = {record.id: role for record, role in rows}
    return [{
        "id": record.id,
        "name": record.name,
        "role": roles[record.id],
        "member_count": db.query(InstitutionMembership).filter_by(institution_id=record.id, status="active").count(),
        "created_at": record.created_at,
    } for record in records]


@router.post("/institutions", response_model=InstitutionOut, status_code=201)
def create_institution(payload: InstitutionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_role(["admin"], current_user)
    institution = Institution(name=payload.name.strip(), created_by=current_user["id"])
    db.add(institution)
    db.flush()
    db.add(InstitutionMembership(institution_id=institution.id, user_id=current_user["id"], role="admin"))
    db.commit()
    db.refresh(institution)
    return {"id": institution.id, "name": institution.name, "role": "admin", "member_count": 1, "created_at": institution.created_at}


@router.get("/institutions/{institution_id}/members", response_model=list[InstitutionMemberOut])
def institution_members(institution_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_institution_role(institution_id, current_user, db, {"admin", "teacher"})
    return (db.query(User.id.label("user_id"), User.name, User.email, InstitutionMembership.role, InstitutionMembership.status)
        .join(InstitutionMembership, InstitutionMembership.user_id == User.id)
        .filter(InstitutionMembership.institution_id == institution_id, InstitutionMembership.status == "active")
        .order_by(User.name)
        .all())


@router.post("/institutions/{institution_id}/members", response_model=InstitutionMemberOut, status_code=201)
def add_institution_member(institution_id: int, payload: InstitutionMemberCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_institution_role(institution_id, current_user, db, {"admin"})
    email = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="The user must sign in before they can be added to an institution.")
    membership = db.query(InstitutionMembership).filter_by(institution_id=institution_id, user_id=user.id).one_or_none()
    if membership and membership.status == "active":
        raise HTTPException(status_code=409, detail="This user is already an active institution member.")
    if membership:
        membership.role = payload.role
        membership.status = "active"
    else:
        membership = InstitutionMembership(institution_id=institution_id, user_id=user.id, role=payload.role)
        db.add(membership)
    db.commit()
    return {"user_id": user.id, "name": user.name, "email": user.email, "role": membership.role, "status": membership.status}


@router.delete("/institutions/{institution_id}/members/{user_id}", status_code=204)
def remove_institution_member(institution_id: int, user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_institution_role(institution_id, current_user, db, {"admin"})
    membership = db.query(InstitutionMembership).filter_by(institution_id=institution_id, user_id=user_id, status="active").one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Institution member not found")
    if membership.role == "teacher":
        linked_classes = (db.query(InstitutionClass.id)
            .join(TeacherClass, InstitutionClass.class_id == TeacherClass.id)
            .filter(InstitutionClass.institution_id == institution_id, TeacherClass.teacher_id == user_id)
            .count())
        if linked_classes:
            raise HTTPException(status_code=409, detail="Unlink the teacher's classes before removing their membership.")
    if membership.role == "student":
        class_ids = [row.class_id for row in db.query(InstitutionClass.class_id).filter_by(institution_id=institution_id).all()]
        if class_ids:
            db.query(Enrollment).filter(
                Enrollment.student_id == user_id,
                Enrollment.class_id.in_(class_ids),
                Enrollment.status == "active",
            ).update({Enrollment.status: "removed"}, synchronize_session=False)
    if membership.role == "admin":
        admin_count = db.query(InstitutionMembership).filter_by(institution_id=institution_id, role="admin", status="active").count()
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="The last institution admin cannot be removed.")
    membership.status = "removed"
    db.commit()


@router.get("/institutions/{institution_id}/classes", response_model=list[InstitutionClassOut])
def institution_classes(institution_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_institution_role(institution_id, current_user, db)
    return (db.query(TeacherClass.id, TeacherClass.name, TeacherClass.language, TeacherClass.teacher_id)
        .join(InstitutionClass, InstitutionClass.class_id == TeacherClass.id)
        .filter(InstitutionClass.institution_id == institution_id)
        .order_by(TeacherClass.name)
        .all())


@router.post("/institutions/{institution_id}/classes/{class_id}", response_model=InstitutionClassOut, status_code=201)
def link_institution_class(institution_id: int, class_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    membership_role = require_institution_role(institution_id, current_user, db, {"admin", "teacher"})
    class_record = db.get(TeacherClass, class_id)
    if class_record is None:
        raise HTTPException(status_code=404, detail="Class not found")
    if membership_role != "admin" and class_record.teacher_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Teachers can only link their own classes.")
    linked = db.query(InstitutionClass).filter_by(institution_id=institution_id, class_id=class_id).one_or_none()
    if linked:
        raise HTTPException(status_code=409, detail="This class is already linked to the institution.")
    db.add(InstitutionClass(institution_id=institution_id, class_id=class_id))
    db.commit()
    return {"id": class_record.id, "name": class_record.name, "language": class_record.language, "teacher_id": class_record.teacher_id}


@router.delete("/institutions/{institution_id}/classes/{class_id}", status_code=204)
def unlink_institution_class(institution_id: int, class_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    membership_role = require_institution_role(institution_id, current_user, db, {"admin", "teacher"})
    linked = db.query(InstitutionClass).filter_by(institution_id=institution_id, class_id=class_id).one_or_none()
    if linked is None:
        raise HTTPException(status_code=404, detail="Institution class link not found")
    class_record = db.get(TeacherClass, class_id)
    if membership_role != "admin" and class_record.teacher_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Teachers can only unlink their own classes.")
    db.delete(linked)
    db.commit()


@router.post("/institutions/{institution_id}/classes/{class_id}/enrollments", response_model=EnrollmentOut, status_code=201)
def institution_enroll_student(institution_id: int, class_id: int, student_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    membership_role = require_institution_role(institution_id, current_user, db, {"admin", "teacher"})
    institution_class = db.query(InstitutionClass).filter_by(institution_id=institution_id, class_id=class_id).one_or_none()
    if institution_class is None:
        raise HTTPException(status_code=404, detail="Class is not linked to this institution.")
    class_record = db.get(TeacherClass, class_id)
    if membership_role == "teacher" and class_record.teacher_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Teachers can only enroll students in their own classes.")
    student_membership = db.query(InstitutionMembership).filter_by(institution_id=institution_id, user_id=student_id, role="student", status="active").one_or_none()
    if student_membership is None:
        raise HTTPException(status_code=422, detail="The user must be an active student member of the institution.")
    existing = db.query(Enrollment).filter_by(class_id=class_id, student_id=student_id, status="active").one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="The student is already enrolled in this class.")
    return enroll_student(class_id=class_id, student_id=student_id, db=db)


@router.get("/institutions/{institution_id}/reports", response_model=InstitutionReportOut)
def institution_report(institution_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_from_headers)):
    require_institution_role(institution_id, current_user, db, {"admin"})
    memberships = db.query(InstitutionMembership).filter_by(institution_id=institution_id, status="active").all()
    class_ids = [row.class_id for row in db.query(InstitutionClass).filter_by(institution_id=institution_id).all()]
    teachers = sum(member.role == "teacher" for member in memberships)
    students = sum(member.role == "student" for member in memberships)
    published_count = db.query(Assignment).filter(Assignment.class_id.in_(class_ids), Assignment.status == "published").count() if class_ids else 0
    attempts = db.query(AssignmentAttempt).join(Assignment, Assignment.id == AssignmentAttempt.assignment_id).filter(Assignment.class_id.in_(class_ids)).all() if class_ids else []
    average_score = sum(attempt.score for attempt in attempts) / len(attempts) if attempts else None
    return InstitutionReportOut(
        member_count=len(memberships),
        teacher_count=teachers,
        student_count=students,
        class_count=len(class_ids),
        published_assignment_count=published_count,
        attempt_count=len(attempts),
        average_score=average_score,
    )
