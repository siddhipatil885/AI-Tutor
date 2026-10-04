"""Strict contracts shared by ingestion, retrieval, and intervention callers."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentType(StrEnum):
    EXPLANATION = "explanation"
    INCORRECT_REASONING = "incorrect_reasoning"
    CORRECT_REASONING = "correct_reasoning"
    INTERVENTION = "intervention"
    HINT = "hint"
    PRACTICE = "practice"
    # Compatibility names for earlier RAG contracts; new corpus data uses the
    # controlled values above.
    CONCEPT_EXPLANATION = "explanation"
    MISCONCEPTION_EXAMPLE = "incorrect_reasoning"
    WORKED_EXAMPLE = "correct_reasoning"
    INTERVENTION_STRATEGY = "intervention"
    GUIDED_HINT = "hint"
    TARGETED_PRACTICE = "practice"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class KnowledgeStage(StrEnum):
    INTERVENTION = "intervention"
    REASSESSMENT = "reassessment"


class KnowledgeMetadata(BaseModel):
    """Traceable pedagogical metadata attached to every source and chunk."""

    model_config = ConfigDict(extra="allow")
    topic: str = Field(min_length=1, examples=["LOOPS"])
    category: str = Field(min_length=1, examples=["LOOPS"])
    concept_id: str = Field(min_length=1, examples=["C-LOOPS"])
    misconception_id: str = Field(min_length=1, examples=["LOOP-01"])
    content_type: ContentType
    difficulty: Difficulty
    stage: KnowledgeStage
    prerequisites: list[str] = Field(default_factory=list)
    source: str = Field(min_length=1, description="Human-readable, traceable source label.")
    educational_purpose: str = Field(min_length=1)


class KnowledgeDocumentInput(BaseModel):
    """A validated source document before chunking or embedding."""

    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(min_length=1)
    misconception_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    content_type: ContentType
    difficulty: Difficulty
    stage: KnowledgeStage
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    educational_purpose: str = Field(min_length=1)
    metadata: KnowledgeMetadata
    source_path: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def non_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content cannot be blank.")
        return value


class KnowledgeChunk(BaseModel):
    """The unit persisted to the future pgvector table."""

    model_config = ConfigDict(extra="forbid")
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    metadata: KnowledgeMetadata
    embedding: list[float] | None = None


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(min_length=1)

    @field_validator("texts")
    @classmethod
    def no_blank_text(cls, values: list[str]) -> list[str]:
        """Return texts unchanged, raising ValueError for blank entries."""
        if any(not value.strip() for value in values):
            raise ValueError("Embedding text cannot be blank.")
        return values


class RetrievalQuery(BaseModel):
    """A retrieval request always starts with a diagnosed misconception."""

    model_config = ConfigDict(extra="forbid")
    misconception_id: str = Field(min_length=1)
    concept_id: str | None = None
    learner_difficulty: Difficulty = Difficulty.BEGINNER
    query_text: str = Field(min_length=1)
    top_k: int = Field(default=4, gt=0, le=20)
    content_types: list[ContentType] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    chunk: KnowledgeChunk
    similarity_score: float = Field(ge=0, le=1)
    match_reasons: list[str] = Field(default_factory=list)


class IngestionReport(BaseModel):
    source_path: str
    documents_seen: int = Field(ge=0)
    documents_validated: int = Field(default=0, ge=0)
    embeddings_generated: int = Field(default=0, ge=0)
    documents_inserted: int = Field(default=0, ge=0)
    documents_updated: int = Field(default=0, ge=0)
    # Retained for callers built against the Stage 1 RAG scaffold. Stage 5
    # writes one curated document per record and does not perform chunking.
    chunks_created: int = Field(default=0, ge=0)
    chunks_upserted: int = Field(default=0, ge=0)
    errors: list[str] = Field(default_factory=list)


class RetrievalContext(BaseModel):
    """Safe, minimal payload for the eventual intervention engine."""

    query: RetrievalQuery
    results: list[RetrievalResult]
    source_labels: list[str]
