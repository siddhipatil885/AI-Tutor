"""Strict contracts shared by ingestion, retrieval, and intervention callers."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentType(StrEnum):
    CONCEPT_EXPLANATION = "concept_explanation"
    MISCONCEPTION_EXAMPLE = "misconception_example"
    WORKED_EXAMPLE = "worked_example"
    INTERVENTION_STRATEGY = "intervention_strategy"
    GUIDED_HINT = "guided_hint"
    TARGETED_PRACTICE = "targeted_practice"


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class KnowledgeMetadata(BaseModel):
    """Traceable pedagogical metadata attached to every source and chunk."""

    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=1, examples=["loops"])
    concept_id: str = Field(min_length=1, examples=["C001"])
    misconception_id: str | None = Field(default=None, examples=["M001"])
    content_type: ContentType
    difficulty: Difficulty
    prerequisites: list[str] = Field(default_factory=list)
    source: str = Field(min_length=1, description="Human-readable, traceable source label.")
    educational_purpose: str = Field(min_length=1)


class KnowledgeDocumentInput(BaseModel):
    """A validated source document before chunking or embedding."""

    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: KnowledgeMetadata
    source_path: str = Field(min_length=1)


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
    chunks_created: int = Field(ge=0)
    chunks_upserted: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)


class RetrievalContext(BaseModel):
    """Safe, minimal payload for the eventual intervention engine."""

    query: RetrievalQuery
    results: list[RetrievalResult]
    source_labels: list[str]
