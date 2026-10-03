from sqlalchemy.orm import Session

from app.models.entities import Diagnosis, Intervention, KnowledgeDocument, Misconception, Question
from app.rag.retrieval import retrieve_for_misconception
from app.schemas import InterventionOut


def create_intervention(db: Session, diagnosis: Diagnosis, question: Question) -> InterventionOut:
    if not diagnosis.misconception_id:
        raise ValueError("An intervention requires a specific misconception diagnosis.")
    misconception = db.get(Misconception, diagnosis.misconception_id)
    docs = retrieve_for_misconception(db, diagnosis.misconception_id, question.concept_id)
    by_type = {doc.content_type: doc.content for doc in docs}
    content = {
        "title": "Check the stopping point of your loop",
        "what_happened": "Your output was one value too long or too short. That points to the loop boundary, not a lack of effort.",
        "explanation": by_type.get("explanation", "In Python, range(start, stop) includes start but stops before stop. The stop value is a fence, not another iteration."),
        "worked_example": by_type.get("worked_example", "range(2, 5) produces 2, 3, 4 — not 5. Trace the values and stop just before the end."),
        "guided_hint": by_type.get("hint", "Before running code, write the first value, then ask: what is the last value strictly before the stop value?"),
        "sources": [doc.source for doc in docs],
    }
    record = Intervention(diagnosis_id=diagnosis.id, content=content, retrieved_document_ids=[doc.id for doc in docs])
    db.add(record)
    db.commit()
    db.refresh(record)
    return InterventionOut(id=record.id, diagnosis_id=diagnosis.id, misconception_id=diagnosis.misconception_id, **content)
