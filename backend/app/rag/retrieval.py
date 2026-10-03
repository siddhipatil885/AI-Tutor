from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import KnowledgeDocument


def retrieve_for_misconception(db: Session, misconception_id: str, concept_id: str, limit: int = 3) -> list[KnowledgeDocument]:
    """Metadata-first retrieval prevents generic material outranking targeted pedagogy."""
    targeted = list(db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.misconception_id == misconception_id).limit(limit)))
    if len(targeted) < limit:
        generic = list(db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.concept_id == concept_id, KnowledgeDocument.misconception_id.is_(None)).limit(limit - len(targeted))))
        targeted.extend(generic)
    return targeted
