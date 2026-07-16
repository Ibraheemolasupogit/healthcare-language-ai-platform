"""Model-free embedding benchmark evidence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from healthcare_language_ai.retrieval_quality.io import stable_id, write_json


def write_hash_embedding_benchmark(
    *, benchmark_dir: Path, output_root: Path, reference_timestamp: datetime
) -> Path:
    benchmark_id = stable_id("EMBEXP", [benchmark_dir, reference_timestamp.isoformat()])
    output_dir = output_root / benchmark_id
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "embedding_benchmark_manifest.json",
        {
            "embedding_benchmark_contract_version": "1.0.0",
            "embedding_benchmark_id": benchmark_id,
            "benchmark_dir": str(benchmark_dir),
            "providers_compared": ["deterministic_hash"],
            "local_model_status": "not_requested",
            "automatic_download_attempted": False,
            "network_connection_attempted": False,
            "reference_timestamp": reference_timestamp.isoformat(),
        },
    )
    return output_dir
