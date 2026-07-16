"""Optional offline local sentence-transformer adapter."""

from __future__ import annotations

import importlib.util
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from healthcare_language_ai.embeddings.model_metadata import directory_checksum
from healthcare_language_ai.embeddings.offline import offline_environment, reject_remote_identifier
from healthcare_language_ai.retrieval_quality.contracts import (
    EmbeddingModelMetadata,
    ModelAvailabilityStatus,
)


class DenseEncoder(Protocol):
    provider_name: str
    provider_version: str
    model_name: str
    model_path: Path
    model_checksum: str
    embedding_dimension: int
    normalise_embeddings: bool
    batch_size: int
    maximum_sequence_length: int | None

    def encode_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def encode_queries(self, texts: Sequence[str]) -> list[list[float]]: ...


class DeterministicTestEncoder:
    provider_name = "deterministic_test_encoder"
    provider_version = "1.0.0"
    model_name = "injected-test-encoder"
    model_path = Path("/tmp/injected-test-encoder")
    model_checksum = "not_applicable"
    normalise_embeddings = True
    batch_size = 8
    maximum_sequence_length = None

    def __init__(
        self, *, dimension: int = 8, invalid: bool = False, mismatch: bool = False
    ) -> None:
        self.embedding_dimension = dimension
        self.invalid = invalid
        self.mismatch = mismatch

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for index, text in enumerate(texts):
            dimension = (
                self.embedding_dimension + 1
                if self.mismatch and index == 0
                else self.embedding_dimension
            )
            if self.invalid:
                vectors.append([math.nan, *([0.0] * (dimension - 1))])
                continue
            seed = sum(ord(char) for char in text)
            raw = [float(((seed + offset * 17) % 23) - 11) for offset in range(dimension)]
            norm = math.sqrt(sum(value * value for value in raw)) or 1.0
            vectors.append([round(value / norm, 8) for value in raw])
        return vectors

    def encode_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts)

    def encode_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts)


def validate_vectors(vectors: list[list[float]], *, expected_dimension: int) -> None:
    for vector in vectors:
        if len(vector) != expected_dimension:
            raise ValueError("embedding dimension is inconsistent")
        if any(not math.isfinite(value) for value in vector):
            raise ValueError("embedding vector contains NaN or infinity")


def inspect_local_model(
    *,
    model_path: Path | str,
    batch_size: int = 16,
    maximum_sequence_length: int | None = None,
) -> EmbeddingModelMetadata:
    path = reject_remote_identifier(model_path)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"local model path does not exist: {path}")
    dependency_available = importlib.util.find_spec("sentence_transformers") is not None
    config_path = path / "config.json"
    if not config_path.exists():
        raise ValueError("model metadata cannot be read: missing config.json")
    loaded = json.loads(config_path.read_text(encoding="utf-8"))
    model_name = str(loaded.get("_name_or_path", path.name))
    dimension = loaded.get("hidden_size")
    if dimension is not None and not isinstance(dimension, int):
        raise ValueError("embedding dimension metadata is invalid")
    return EmbeddingModelMetadata(
        provider_name="sentence_transformer",
        provider_version="optional-local",
        model_name=model_name,
        model_path=str(path),
        model_checksum=directory_checksum(path),
        embedding_dimension=dimension,
        normalise_embeddings=True,
        batch_size=batch_size,
        maximum_sequence_length=maximum_sequence_length,
        pooling="mean_pooling_when_supported",
        availability_status=ModelAvailabilityStatus.AVAILABLE
        if dependency_available
        else ModelAvailabilityStatus.UNAVAILABLE,
        dependency_available=dependency_available,
        offline_environment=offline_environment(),
        automatic_download_attempted=False,
        network_connection_attempted=False,
    )


def encode_with_injected_encoder(
    encoder: DenseEncoder, texts: Sequence[str], *, query: bool = False
) -> list[list[float]]:
    vectors = encoder.encode_queries(texts) if query else encoder.encode_documents(texts)
    validate_vectors(vectors, expected_dimension=encoder.embedding_dimension)
    return vectors
