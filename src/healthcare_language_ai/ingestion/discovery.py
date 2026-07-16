"""Source discovery for Milestone 2 synthetic datasets."""

from __future__ import annotations

from pathlib import Path

from healthcare_language_ai.exceptions import ConfigurationError
from healthcare_language_ai.ingestion.contracts import IngestionFile, IngestionSource
from healthcare_language_ai.synthetic.manifest import sha256_file

REQUIRED_SOURCE_FILES = [
    "clinical_documents.jsonl",
    "document_annotations.jsonl",
    "dataset_manifest.json",
    "data_quality_report.json",
    "README.md",
]


def discover_source(source_dir: Path, *, follow_symlinks: bool) -> IngestionSource:
    """Validate a single dataset directory and return deterministic file inventory."""
    resolved = source_dir.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        msg = f"source directory does not exist: {source_dir}"
        raise ConfigurationError(msg)
    files: list[IngestionFile] = []
    for file_name in REQUIRED_SOURCE_FILES:
        path = resolved / file_name
        if not path.exists():
            msg = f"required source file missing: {file_name}"
            raise ConfigurationError(msg)
        if path.is_symlink() and not follow_symlinks:
            msg = f"symlink source files are not followed: {file_name}"
            raise ConfigurationError(msg)
        stat = path.stat()
        files.append(
            IngestionFile(
                file_name=file_name,
                path=path,
                size_bytes=stat.st_size,
                sha256=sha256_file(path),
            )
        )
    manifest_checksum = next(
        file.sha256 for file in files if file.file_name == "dataset_manifest.json"
    )
    return IngestionSource(
        source_dir=resolved,
        files=sorted(files, key=lambda item: item.file_name),
        source_manifest_checksum=manifest_checksum,
    )
