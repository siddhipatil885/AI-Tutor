from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import Concept, KnowledgeDocument, Misconception, Question, User


def seed(db: Session) -> None:
    if not db.get(User, 1):
        db.add(User(id=1, name="Demo learner"))
    if not db.get(Concept, "C001"):
        db.add(Concept(id="C001", name="Python loop boundaries", description="How range start and stop values determine iterations."))
    if not db.get(Misconception, "M001"):
        db.add(Misconception(id="M001", concept_id="C001", name="Off-by-one loop boundary", student_friendly_name="Checking where a loop stops", description="Treating range's stop value as inclusive."))
    if not db.scalars(select(KnowledgeDocument).limit(1)).first():
        db.add_all([
            KnowledgeDocument(misconception_id="M001", concept_id="C001", content_type="explanation", difficulty="beginner", source="Re:Learn curated loop-boundary note", educational_purpose="correct inclusive-stop misconception", content="Python's range(start, stop) begins at start and ends immediately before stop. This makes stop an exclusive boundary."),
            KnowledgeDocument(misconception_id="M001", concept_id="C001", content_type="worked_example", difficulty="beginner", source="Re:Learn curated traced example", educational_purpose="make loop bounds visible", content="Trace range(2, 5): start at 2, then 3, then 4. The next value would be 5, but 5 is the stop boundary, so it is not produced."),
            KnowledgeDocument(misconception_id="M001", concept_id="C001", content_type="hint", difficulty="beginner", source="Re:Learn guided practice prompt", educational_purpose="encourage self-correction", content="Draw a small fence at the stop number. Every value before the fence is allowed; the number on the fence is not."),
        ])
    if not db.scalars(select(Question).where(Question.question_kind == "initial")).first():
        db.add(Question(concept_id="C001", prompt="What does this Python code print?\n\nfor i in range(1, 4):\n    print(i)", expected_answer="1 2 3", explanation="range(1, 4) includes 1, 2, and 3, then stops before 4.", difficulty="beginner", question_kind="initial"))
    db.commit()
