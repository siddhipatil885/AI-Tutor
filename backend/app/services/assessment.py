from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import Assignment


QUESTION_LIBRARY = {
    "python": {
        "loop boundaries": {
            "mcq": {
                "prompt": "What values does range(2, 6) produce?",
                "correct_answer": "2, 3, 4, 5",
                "explanation": "The stop value is exclusive, so 6 is not included.",
            },
            "output_prediction": {
                "prompt": "Predict the output of: for n in range(1, 4): print(n)",
                "correct_answer": "1\n2\n3",
                "explanation": "The loop runs from 1 to 3, stopping before 4.",
            },
        },
        "conditionals": {
            "mcq": {
                "prompt": "Which condition is true when x equals 10?",
                "correct_answer": "x >= 10",
                "explanation": "The expression is true when x is equal to or larger than 10.",
            },
            "output_prediction": {
                "prompt": "Predict the output of: x = 7; if x > 5: print('yes') else: print('no')",
                "correct_answer": "yes",
                "explanation": "7 is greater than 5, so the if branch executes.",
            },
        },
        "functions": {
            "mcq": {
                "prompt": "A function with a return statement can be used to:",
                "correct_answer": "produce a value for the caller",
                "explanation": "Functions can compute and return values for reuse.",
            },
            "output_prediction": {
                "prompt": "Predict the output of: def add(a, b): return a + b; print(add(2, 3))",
                "correct_answer": "5",
                "explanation": "The function returns the sum, which is displayed by print.",
            },
        },
    }
}


def create_assignment(teacher_id: int, class_id: int, title: str, language: str = "python", difficulty: str = "beginner", question_count: int = 2, question_types: list[str] | None = None, db: Session | None = None) -> dict:
    generated = generate_assessment(
        language=language,
        topics=["loop boundaries", "conditionals"],
        difficulty=difficulty,
        question_count=question_count,
        question_types=question_types or ["mcq", "output_prediction"],
    )
    session = db or SessionLocal()
    try:
        record = Assignment(
            class_id=class_id,
            teacher_id=teacher_id,
            title=title,
            language=generated["language"],
            difficulty=generated["difficulty"],
            question_count=len(generated["questions"]),
            question_types=question_types or ["mcq", "output_prediction"],
            questions=generated["questions"],
            status="draft",
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return {
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
        }
    finally:
        if db is None:
            session.close()


def generate_assessment(language: str, topics: list[str], difficulty: str, question_count: int, question_types: list[str] | None = None) -> dict:
    language_key = (language or "python").lower()
    normalized_topics = topics or ["loop boundaries"]
    question_types = question_types or ["mcq"]
    questions = []

    for index in range(max(1, question_count)):
        topic = normalized_topics[index % len(normalized_topics)]
        question_type = question_types[index % len(question_types)]
        topic_questions = QUESTION_LIBRARY.get(language_key, QUESTION_LIBRARY["python"]).get(topic, QUESTION_LIBRARY["python"]["loop boundaries"])
        template = topic_questions.get(question_type, topic_questions["mcq"])
        misconception_ids = ["M001"] if topic == "loop boundaries" else ["M002"] if topic == "conditionals" else ["C003"]
        questions.append(
            {
                "id": index + 1,
                "language": language_key,
                "topic": topic,
                "question_type": question_type,
                "difficulty": difficulty,
                "prompt": template["prompt"],
                "correct_answer": template["correct_answer"],
                "explanation": template["explanation"],
                "misconception_ids": misconception_ids,
            }
        )

    return {
        "language": language_key,
        "difficulty": difficulty,
        "questions": questions,
    }
