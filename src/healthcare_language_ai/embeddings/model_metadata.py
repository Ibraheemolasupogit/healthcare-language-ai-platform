"""Local embedding model metadata inspection."""

from __future__ import annotations

import hashlib
from pathlib import Path

from healthcare_language_ai.retrieval_quality.contracts import (
    EmbeddingModelMetadata,
    ModelAvailabilityStatus,
)


def directory_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(str(file_path.relative_to(path)).encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def metadata_for_unavailable(path: Path, *, reason: str) -> EmbeddingModelMetadata:
    from healthcare_language_ai.embeddings.offline import offline_environment

    return EmbeddingModelMetadata(
        provider_name="sentence_transformer",
        provider_version="not_available",
        model_name=reason,
        model_path=str(path),
        model_checksum="not_applicable",
        embedding_dimension=None,
        normalise_embeddings=True,
        batch_size=16,
        maximum_sequence_length=None,
        pooling="not_applicable",
        availability_status=ModelAvailabilityStatus.UNAVAILABLE,
        dependency_available=False,
        offline_environment=offline_environment(),
        automatic_download_attempted=False,
        network_connection_attempted=False,
    )
