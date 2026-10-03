"""Configuration for the future misconception-scoped RAG runtime."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    """Environment-backed settings; loading these does not initialize a model."""

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = Field(default=384, gt=0)
    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=80, ge=0)
    default_top_k: int = Field(default=4, gt=0, le=20)
    similarity_threshold: float = Field(default=0.55, ge=0, le=1)
    knowledge_table: str = "rag_knowledge_chunks"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")


@lru_cache
def get_rag_settings() -> RagSettings:
    return RagSettings()
