"""Configuration for the future misconception-scoped RAG runtime."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


EMBEDDING_DIMENSIONS = 384


class RagSettings(BaseSettings):
    """Environment-backed settings; loading these does not initialize a model."""

    embedding_model: str = "all-MiniLM-L6-v2"
    # pgvector dimensions are part of the database schema. This initial RAG
    # contract is fixed to all-MiniLM-L6-v2's 384-dimensional output; changing
    # it requires an explicit data migration, not an environment override.
    embedding_dimensions: Literal[384] = EMBEDDING_DIMENSIONS
    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=80, ge=0)
    default_top_k: int = Field(default=4, gt=0, le=20)
    similarity_threshold: float = Field(default=0.55, ge=0, le=1)
    knowledge_table: str = "knowledge_documents"
    ingestion_version: str = "1.0.0"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")


@lru_cache
def get_rag_settings() -> RagSettings:
    """Return cached RAG settings loaded from the environment and .env file."""
    return RagSettings()
