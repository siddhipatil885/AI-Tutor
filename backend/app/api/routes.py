from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Assessment, Diagnosis, Intervention, Question, Submission
from app.schemas import (CodeDiagnosisCreate, CodeSubmissionCreate, DiagnosisOut, InterventionOut, JudgeResultOut, LearnerOut, ProgressOut, QuestionCreate, QuestionOut, ReassessmentCreate, ReassessmentOut, SubmissionCreate, SubmissionOut)
from app.services.diagnosis import diagnose, normalize
from app.services.intervention import create_intervention
from app.services.judge import judge_python_submission
from app.services.learner import apply_assessment, profile_for, record_concept_success

router = APIRouter(prefix="/api")


def question_out(q: Question) -> QuestionOut:
    return QuestionOut(id=q.id, concept_id=q.concept_id, prompt=q.prompt, expected_answer=q.expected_answer, explanation=q.explanation, difficulty=q.difficulty, question_kind=q.question_kind)


def diagnosis_out(d: Diagnosis) -> DiagnosisOut:
    name = "Loop boundary / off-by-one" if d.misconception_id == "M001" else None
    return DiagnosisOut(id=d.id, is_correct=d.is_correct, misconception_id=d.misconception_id, misconception_name=name, confidence=d.confidence, evidence=d.evidence, error_type=d.error_type, needs_intervention=d.needs_intervention)


@router.get("/questions/default", response_model=QuestionOut)
def default_question(db: Session = Depends(get_db)):
    question = db.query(Question).filter_by(question_kind="initial").first()
    if not question: raise HTTPException(404, "No demo question available")
    return question_out(question)


@router.post("/questions", response_model=QuestionOut, status_code=201)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    q = Question(**payload.model_dump())
    db.add(q); db.commit(); db.refresh(q)
    return question_out(q)


@router.get("/questions/{question_id}", response_model=QuestionOut)
def get_question(question_id: int, db: Session = Depends(get_db)):
    q = db.get(Question, question_id)
    if not q: raise HTTPException(404, "Question not found")
    return question_out(q)


@router.post("/submissions", response_model=SubmissionOut, status_code=201)
def submit(payload: SubmissionCreate, db: Session = Depends(get_db)):
    q = db.get(Question, payload.question_id)
    if not q: raise HTTPException(404, "Question not found")
    record = Submission(**payload.model_dump())
    db.add(record); db.flush()
    result = diagnose(q.expected_answer, payload.answer, payload.reasoning)
    diagnosis = Diagnosis(submission_id=record.id, is_correct=result.is_correct, misconception_id=result.misconception_id, confidence=result.confidence, evidence=result.evidence, error_type=result.error_type, needs_intervention=result.needs_intervention)
    db.add(diagnosis); db.commit(); db.refresh(diagnosis)
    if result.is_correct:
        profile = profile_for(db, payload.user_id)
        record_concept_success(db, profile, q.concept_id, result.evidence)
    elif result.misconception_id:
        profile = profile_for(db, payload.user_id)
        active = list(profile.active_misconceptions or [])
        if result.misconception_id not in active: active.append(result.misconception_id)
        profile.active_misconceptions = active; db.commit()
    return SubmissionOut(id=record.id, diagnosis=diagnosis_out(diagnosis))


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, db: Session = Depends(get_db)):
    submission = db.get(Submission, submission_id)
    if not submission: raise HTTPException(404, "Submission not found")
    d = db.query(Diagnosis).filter_by(submission_id=submission_id).first()
    return SubmissionOut(id=submission.id, diagnosis=diagnosis_out(d))


@router.post("/diagnose", response_model=DiagnosisOut)
def direct_diagnose(payload: SubmissionCreate, db: Session = Depends(get_db)):
    q = db.get(Question, payload.question_id)
    if not q: raise HTTPException(404, "Question not found")
    return diagnose(q.expected_answer, payload.answer, payload.reasoning)


@router.post("/judge/python", response_model=JudgeResultOut)
def judge_python(payload: CodeSubmissionCreate):
    if payload.language.lower() != "python":
        raise HTTPException(400, "This judge currently supports Python only.")
    return judge_python_submission(payload.code, payload.problem_id, payload.function_name, payload.tests)


@router.post("/diagnose/code")
def diagnose_code(payload: CodeDiagnosisCreate):
    try:
        if payload.language.lower() != "python":
            raise HTTPException(400, "Only Python code is supported for diagnosis.")
        if not payload.code or not payload.code.strip():
            raise HTTPException(400, "Empty code provided.")
        
        import sys
        import os
        # Add the root directory to sys.path so we can import 'ml'
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            
        from ml.src.inference import predict
        model_path = os.path.join(root_dir, "ml", "models", "exp5_fusion.pkl")
        return predict(code=payload.code, problem_context=payload.problem_id, model_path=model_path)
    except HTTPException:
        raise
    except ImportError as e:
        raise HTTPException(500, f"ML subsystem not configured or missing dependencies: {e}")
    except Exception as e:
        raise HTTPException(500, f"Inference failed: {e}")


@router.post("/interventions", response_model=InterventionOut, status_code=201)
def intervention(submission_id: int, db: Session = Depends(get_db)):
    d = db.query(Diagnosis).filter_by(submission_id=submission_id).first()
    submission = db.get(Submission, submission_id)
    if not d or not submission: raise HTTPException(404, "Submission or diagnosis not found")
    if not d.needs_intervention: raise HTTPException(422, "This diagnosis does not justify a targeted intervention.")
    return create_intervention(db, d, db.get(Question, submission.question_id))


@router.post("/reassessment", response_model=ReassessmentOut)
def reassess(payload: ReassessmentCreate, db: Session = Depends(get_db)):
    intervention = db.get(Intervention, payload.intervention_id)
    if not intervention: raise HTTPException(404, "Intervention not found")
    diagnosis = db.get(Diagnosis, intervention.diagnosis_id)
    if not diagnosis or not diagnosis.misconception_id: raise HTTPException(422, "No misconception available for reassessment")
    assessment = db.get(Assessment, payload.assessment_id) if payload.assessment_id else None
    if not assessment:
        follow_up = Question(concept_id="C001", prompt="A different loop: What values are printed by `for n in range(3, 7): print(n)`?", expected_answer="3 4 5 6", explanation="The start is included; the stop value 7 is excluded.", difficulty="beginner", question_kind="reassessment")
        db.add(follow_up); db.flush()
        assessment = Assessment(user_id=payload.user_id, misconception_id=diagnosis.misconception_id, question_id=follow_up.id, status="pending", evidence=[])
        db.add(assessment); db.commit(); db.refresh(assessment)
        return ReassessmentOut(assessment_id=assessment.id, question=question_out(follow_up), status="pending", evidence=["This follow-up changes the numbers while testing the same exclusive-stop idea."])
    question = db.get(Question, assessment.question_id)
    if payload.answer is None: raise HTTPException(422, "Submit an answer for this reassessment.")
    correct = normalize(payload.answer) == normalize(question.expected_answer)
    evidence = ["The follow-up answer uses the exclusive stop boundary correctly."] if correct else ["The follow-up answer still includes or omits a boundary value."]
    profile = profile_for(db, payload.user_id)
    status = apply_assessment(db, profile, assessment.misconception_id, correct, evidence)
    assessment.answer, assessment.status, assessment.evidence = payload.answer, status, evidence
    db.commit()
    return ReassessmentOut(assessment_id=assessment.id, question=question_out(question), status=status, evidence=evidence)


@router.get("/learner/{user_id}", response_model=LearnerOut)
def learner(user_id: int, db: Session = Depends(get_db)):
    p = profile_for(db, user_id)
    return LearnerOut(user_id=user_id, mastery=p.mastery, active_misconceptions=p.active_misconceptions, resolved_misconceptions=p.resolved_misconceptions, trajectory=p.trajectory)


@router.get("/learner/{user_id}/misconceptions")
def misconceptions(user_id: int, db: Session = Depends(get_db)):
    p = profile_for(db, user_id)
    return {"active": p.active_misconceptions, "resolved": p.resolved_misconceptions}


@router.get("/learner/{user_id}/progress", response_model=ProgressOut)
def progress(user_id: int, db: Session = Depends(get_db)):
    p = profile_for(db, user_id)
    return ProgressOut(active_count=len(p.active_misconceptions), resolved_count=len(p.resolved_misconceptions), mastery=p.mastery, trajectory=p.trajectory)
