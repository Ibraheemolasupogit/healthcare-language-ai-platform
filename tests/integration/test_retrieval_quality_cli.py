from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app

BENCHMARK = "tests/fixtures/retrieval-quality/benchmark"
REGISTRY = "config/retrieval-configurations.yaml"


def test_retrieval_quality_cli_end_to_end(runner: CliRunner, tmp_path: Path) -> None:
    holdout = tmp_path / "holdout"
    result = runner.invoke(
        app,
        [
            "holdout-generate",
            "--count",
            "40",
            "--seed",
            "7026",
            "--output-dir",
            str(holdout),
            "--reference-timestamp",
            "2026-01-09T09:00:00+00:00",
        ],
    )
    assert result.exit_code == 0
    assert "Document count: 40" in result.output
    assert runner.invoke(app, ["holdout-validate", "--holdout-dir", str(holdout)]).exit_code == 0
    assert runner.invoke(app, ["holdout-summary", "--holdout-dir", str(holdout)]).exit_code == 0

    benchmark = tmp_path / "benchmark"
    query_fixture = runner.invoke(
        app,
        [
            "retrieval-quality-query-fixtures",
            "--output-dir",
            str(benchmark),
            "--holdout-dir",
            str(holdout),
        ],
    )
    assert query_fixture.exit_code == 0
    assert "Query count: 95" in query_fixture.output

    expanded = runner.invoke(
        app,
        [
            "retrieval-query-expand",
            "--query-set",
            str(benchmark / "retrieval_queries_v2.jsonl"),
            "--output-dir",
            str(tmp_path / "expanded"),
        ],
    )
    assert expanded.exit_code == 0

    experiment_root = tmp_path / "experiments"
    experiment = runner.invoke(
        app,
        [
            "retrieval-benchmark-run",
            "--configuration-id",
            "feature_reranked_hybrid_v1",
            "--benchmark-dir",
            str(benchmark),
            "--output-root",
            str(experiment_root),
            "--reference-timestamp",
            "2026-01-10T09:00:00+00:00",
        ],
    )
    assert experiment.exit_code == 0
    experiment_dir = next(experiment_root.iterdir())
    assert (
        runner.invoke(
            app, ["retrieval-benchmark-validate", "--experiment-dir", str(experiment_dir)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["retrieval-benchmark-summary", "--experiment-dir", str(experiment_dir)]
        ).exit_code
        == 0
    )

    comparison_root = tmp_path / "comparison"
    comparison = runner.invoke(
        app,
        [
            "retrieval-compare",
            "--benchmark-dir",
            str(benchmark),
            "--configuration-registry",
            REGISTRY,
            "--output-root",
            str(comparison_root),
            "--reference-timestamp",
            "2026-01-11T09:00:00+00:00",
        ],
    )
    assert comparison.exit_code == 0
    comparison_dir = next(comparison_root.iterdir())
    assert (
        runner.invoke(
            app, ["retrieval-compare-validate", "--comparison-dir", str(comparison_dir)]
        ).exit_code
        == 0
    )
    approval = runner.invoke(app, ["retrieval-approval", "--comparison-dir", str(comparison_dir)])
    assert approval.exit_code == 0
    assert "Approved for future RAG prototype: false" in approval.output
    assert (
        runner.invoke(
            app,
            [
                "retrieval-review-pack",
                "--benchmark-dir",
                str(benchmark),
                "--output-dir",
                str(tmp_path / "review"),
            ],
        ).exit_code
        == 0
    )


def test_embedding_model_inspect_rejects_invalid_path(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["embedding-model-inspect", "--model-path", str(tmp_path / "missing-model")],
    )
    assert result.exit_code != 0


def test_embedding_benchmark_model_free(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "embedding-benchmark-run",
            "--benchmark-dir",
            BENCHMARK,
            "--output-root",
            str(tmp_path / "embedding"),
            "--reference-timestamp",
            "2026-01-10T09:00:00+00:00",
        ],
    )
    assert result.exit_code == 0
