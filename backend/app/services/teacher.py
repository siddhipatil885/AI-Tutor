from __future__ import annotations

from statistics import mean

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import Assignment, Enrollment, Lab, LabSubmission, TeacherClass


TOPIC_ALIASES = {
    "C001": "loop boundaries",
    "M001": "loop boundaries",
    "M002": "conditionals",
    "C002": "conditionals",
    "C003": "functions",
    "C004": "lists",
}


def create_class(teacher_id: int, name: str, language: str = "python", description: str | None = None, db: Session | None = None) -> dict:
    session = db or SessionLocal()
    try:
        record = TeacherClass(teacher_id=teacher_id, name=name, language=language, description=description)
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "teacher_id": record.teacher_id,
            "name": record.name,
            "language": record.language,
            "description": record.description,
        }
    finally:
        if db is None:
            session.close()


def enroll_student(class_id: int, student_id: int, db: Session | None = None) -> dict:
    session = db or SessionLocal()
    try:
        record = Enrollment(class_id=class_id, student_id=student_id, status="active")
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "class_id": record.class_id,
            "student_id": record.student_id,
            "status": record.status,
        }
    finally:
        if db is None:
            session.close()


def list_classes(teacher_id: int | None = None, db: Session | None = None) -> list[dict]:
    session = db or SessionLocal()
    try:
        query = session.query(TeacherClass)
        if teacher_id is not None:
            query = query.filter_by(teacher_id=teacher_id)
        return [{
            "id": record.id,
            "teacher_id": record.teacher_id,
            "name": record.name,
            "language": record.language,
            "description": record.description,
        } for record in query.order_by(TeacherClass.id).all()]
    finally:
        if db is None:
            session.close()


def create_lab(teacher_id: int, class_id: int, title: str, language: str = "python", concept: str = "general", difficulty: str = "beginner", instructions: str | None = None, duration_minutes: int = 30, status: str = "draft", db: Session | None = None) -> dict:
    session = db or SessionLocal()
    try:
        record = Lab(
            teacher_id=teacher_id,
            class_id=class_id,
            title=title,
            language=language,
            concept=concept,
            difficulty=difficulty,
            instructions=instructions,
            duration_minutes=duration_minutes,
            status=status,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "teacher_id": record.teacher_id,
            "class_id": record.class_id,
            "title": record.title,
            "language": record.language,
            "concept": record.concept,
            "difficulty": record.difficulty,
            "instructions": record.instructions,
            "duration_minutes": record.duration_minutes,
            "status": record.status,
        }
    finally:
        if db is None:
            session.close()


def list_labs(class_id: int | None = None, teacher_id: int | None = None, db: Session | None = None) -> list[dict]:
    session = db or SessionLocal()
    try:
        query = session.query(Lab)
        if class_id is not None:
            query = query.filter_by(class_id=class_id)
        if teacher_id is not None:
            query = query.filter_by(teacher_id=teacher_id)
        return [{
            "id": record.id,
            "teacher_id": record.teacher_id,
            "class_id": record.class_id,
            "title": record.title,
            "language": record.language,
            "concept": record.concept,
            "difficulty": record.difficulty,
            "instructions": record.instructions,
            "duration_minutes": record.duration_minutes,
            "status": record.status,
        } for record in query.order_by(Lab.id).all()]
    finally:
        if db is None:
            session.close()


def list_student_labs(student_id: int, db: Session | None = None) -> list[dict]:
    session = db or SessionLocal()
    try:
        class_ids = [row.class_id for row in session.query(Enrollment).filter_by(student_id=student_id, status="active").all()]
        if not class_ids:
            return []
        records = (session.query(Lab, TeacherClass.name.label("class_name"))
            .join(TeacherClass, TeacherClass.id == Lab.class_id)
            .filter(Lab.class_id.in_(class_ids))
            .order_by(Lab.id)
            .all())
        return [{
            "id": lab.id,
            "teacher_id": lab.teacher_id,
            "class_id": lab.class_id,
            "class_name": class_name,
            "title": lab.title,
            "language": lab.language,
            "concept": lab.concept,
            "difficulty": lab.difficulty,
            "instructions": lab.instructions,
            "duration_minutes": lab.duration_minutes,
            "status": lab.status,
        } for lab, class_name in records]
    finally:
        if db is None:
            session.close()


def submit_lab_progress(lab_id: int, student_id: int, answer: str, reflection: str | None = None, status: str = "submitted", db: Session | None = None) -> dict:
    session = db or SessionLocal()
    try:
        allowed_statuses = {"submitted", "in_progress", "needs_revision", "completed"}
        if status not in allowed_statuses:
            raise ValueError(f"Unsupported lab submission status: {status}")

        lab = session.query(Lab).filter_by(id=lab_id).one_or_none()
        if lab is None:
            raise ValueError(f"Lab {lab_id} not found")

        enrollment = session.query(Enrollment).filter_by(student_id=student_id, class_id=lab.class_id, status="active").one_or_none()
        if enrollment is None:
            raise ValueError(f"Student {student_id} is not enrolled in the lab’s class")

        record = LabSubmission(student_id=student_id, lab_id=lab_id, answer=answer, reflection=reflection, status=status)
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "student_id": record.student_id,
            "lab_id": record.lab_id,
            "answer": record.answer,
            "reflection": record.reflection,
            "status": record.status,
        }
    finally:
        if db is None:
            session.close()


def update_lab_status(lab_id: int, status: str, db: Session | None = None) -> dict:
    session = db or SessionLocal()
    try:
        allowed_statuses = {"draft", "scheduled", "active", "paused", "completed", "archived"}
        if status not in allowed_statuses:
            raise ValueError(f"Unsupported lab status: {status}")
        record = session.query(Lab).filter_by(id=lab_id).one_or_none()
        if record is None:
            raise ValueError(f"Lab {lab_id} not found")
        record.status = status
        session.commit()
        session.refresh(record)
        return {
            "id": record.id,
            "teacher_id": record.teacher_id,
            "class_id": record.class_id,
            "title": record.title,
            "language": record.language,
            "concept": record.concept,
            "difficulty": record.difficulty,
            "instructions": record.instructions,
            "duration_minutes": record.duration_minutes,
            "status": record.status,
        }
    finally:
        if db is None:
            session.close()


def list_class_assignments(class_id: int, db: Session | None = None) -> list[dict]:
    session = db or SessionLocal()
    try:
        records = session.query(Assignment).filter_by(class_id=class_id).order_by(Assignment.id).all()
        return [{
            "id": record.id,
            "class_id": record.class_id,
            "teacher_id": record.teacher_id,
            "title": record.title,
            "language": record.language,
            "difficulty": record.difficulty,
            "question_count": record.question_count,
            "question_types": record.question_types,
            "questions": record.questions,
            "status": record.status,
        } for record in records]
    finally:
        if db is None:
            session.close()


def list_student_assignments(student_id: int, db: Session | None = None) -> list[dict]:
    session = db or SessionLocal()
    try:
        class_ids = [row.class_id for row in session.query(Enrollment).filter_by(student_id=student_id, status="active").all()]
        if not class_ids:
            return []
        records = (session.query(Assignment, TeacherClass.name.label("class_name"))
            .join(TeacherClass, TeacherClass.id == Assignment.class_id)
            .filter(Assignment.class_id.in_(class_ids))
            .order_by(Assignment.id)
            .all())
        return [{
            "id": assignment.id,
            "class_id": assignment.class_id,
            "class_name": class_name,
            "teacher_id": assignment.teacher_id,
            "title": assignment.title,
            "language": assignment.language,
            "difficulty": assignment.difficulty,
            "question_count": assignment.question_count,
            "question_types": assignment.question_types,
            "questions": assignment.questions,
            "status": assignment.status,
        } for assignment, class_name in records]
    finally:
        if db is None:
            session.close()


def build_teacher_dashboard(students: list[dict]) -> dict:
    if not students:
        return {
            "total_students": 0,
            "active_students": 0,
            "average_assessment_performance": None,
            "average_mastery": None,
            "average_concept_mastery": None,
            "assignment_completion_rates": {},
            "weak_topics": [],
            "at_risk_students": [],
        }

    mastery_values = []
    assessment_performance = []
    topic_scores: dict[str, list[float]] = {}
    topic_students: dict[str, list[str]] = {}
    topic_misconceptions: dict[str, set[str]] = {}

    for student in students:
        mastery = student.get("mastery", {}) or {}
        if mastery:
            mastery_values.append(mean(float(value) for value in mastery.values()))
        if student.get("assessment_performance") is not None:
            assessment_performance.append(float(student["assessment_performance"]))
        for concept_id, score in (mastery or {}).items():
            topic = TOPIC_ALIASES.get(concept_id, "general concept")
            topic_scores.setdefault(topic, []).append(float(score))
            topic_students.setdefault(topic, []).append(student["name"])
            for misconception in student.get("active_misconceptions", []):
                topic_misconceptions.setdefault(topic, set()).add(misconception)

    average_mastery = mean(mastery_values) if mastery_values else 0.0
    weak_topics: list[dict] = []
    for topic, scores in sorted(topic_scores.items(), key=lambda entry: mean(entry[1])):
        if mean(scores) < 0.75:
            weak_topics.append(
                {
                    "topic": topic,
                    "mastery": round(mean(scores), 3),
                    "weak_students": sorted(set(topic_students.get(topic, []))),
                    "misconception_ids": sorted(topic_misconceptions.get(topic, set())),
                }
            )

    at_risk_students = []
    for student in students:
        mastery = student.get("mastery", {}) or {}
        concept_mastery = mean(float(score) for score in mastery.values()) if mastery else 0.0
        active_count = len(student.get("active_misconceptions", []) or [])
        if (mastery and concept_mastery < 0.6) or active_count >= 2:
            reasons = []
            if concept_mastery < 0.6:
                reasons.append("mastery below the class baseline")
            if active_count >= 2:
                reasons.append("multiple active misconceptions")
            at_risk_students.append(
                {
                    "student": student["name"],
                    "risk_score": round(1 - concept_mastery + (active_count * 0.12), 3),
                    "reasons": reasons,
                }
            )

    active_students = sum(bool(student.get("has_submission")) for student in students)

    return {
        "total_students": len(students),
        "active_students": active_students,
        "average_assessment_performance": round(mean(assessment_performance), 1) if assessment_performance else None,
        "average_mastery": round(average_mastery, 3) if mastery_values else None,
        "average_concept_mastery": round(average_mastery, 3) if mastery_values else None,
        "assignment_completion_rates": {},
        "weak_topics": weak_topics[:4],
        "at_risk_students": at_risk_students,
    }
