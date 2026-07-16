"""Typed contracts for local embedding evidence."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmbeddingVector(EmbeddingBaseModel):
    retrieval_unit_id: str
    embedding_provider: str
    embedding_dimension: int = Field(gt=0)
    vector: list[float]
    vector_norm: float
    hash_embedding_version: str


class EmbeddingMetadata(EmbeddingBaseModel):
    embedding_provider: str
    embedding_dimension: int
    hash_embedding_version: str
    tokeniser_version: str
    ngram_range: list[int]
    model_path: str | None = None
    model_checksum: str | None = None
    automatic_download_permitted: bool
