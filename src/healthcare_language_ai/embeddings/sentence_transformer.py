"""Optional local sentence-transformer adapter.

The default test and fixture path never imports sentence-transformers. This
adapter only validates an already-present local model path and accepts an injected
encoder for tests or future local use.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from healthcare_language_ai.synthetic.manifest import sha256_file


def validate_local_model_path(model_path: Path) -> str:
    if not model_path.exists():
        msg = f"local sentence-transformer model path does not exist: {model_path}"
        raise FileNotFoundError(msg)
    if model_path.is_file():
        return sha256_file(model_path)
    files = sorted(path for path in model_path.rglob("*") if path.is_file())
    if not files:
        msg = f"local sentence-transformer model path contains no files: {model_path}"
        raise ValueError(msg)
    joined = "".join(sha256_file(path) for path in files)
    import hashlib

    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def encode_with_injected_encoder(
    texts: list[str], encoder: Callable[[list[str]], list[list[float]]]
) -> list[list[float]]:
    return encoder(texts)
