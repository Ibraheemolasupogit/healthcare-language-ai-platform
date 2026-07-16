from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app

M7_BENCHMARK = "tests/fixtures/retrieval-quality/benchmark"
M7_EXPERIMENT = "tests/fixtures/retrieval-quality/experiments/RETEXP-fb2b3ecba8151d28fa6f3f9a"
REGISTRY = "config/retrieval-remediation-configurations.yaml"


def test_retrieval_remediation_cli_end_to_end(runner: CliRunner, tmp_path: Path) -> None:
    failure_root = tmp_path / "failures"
    failure = runner.invoke(
        app,
        [
            "retrieval-failure-analyse",
            "--benchmark-dir",
            M7_BENCHMARK,
            "--experiment-dir",
            M7_EXPERIMENT,
            "--output-root",
            str(failure_root),
        ],
    )
    assert failure.exit_code == 0
    failure_dir = next(failure_root.iterdir())
    assert (
        runner.invoke(
            app, ["retrieval-failure-validate", "--failure-dir", str(failure_dir)]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["retrieval-failure-summary", "--failure-dir", str(failure_dir)]
        ).exit_code
        == 0
    )

    benchmark = tmp_path / "benchmark-v2.1"
    upgraded = runner.invoke(
        app,
        [
            "retrieval-benchmark-upgrade",
            "--benchmark-dir",
            M7_BENCHMARK,
            "--output-dir",
            str(benchmark),
        ],
    )
    assert upgraded.exit_code == 0
    assert (
        runner.invoke(
            app,
            ["retrieval-remediation-validate", "--benchmark-dir", str(benchmark)],
        ).exit_code
        == 0
    )

    experiment_root = tmp_path / "experiments"
    experiment = runner.invoke(
        app,
        [
            "retrieval-remediation-run",
            "--configuration-id",
            "abstaining_ensemble_v1",
            "--benchmark-dir",
            str(benchmark),
            "--output-root",
            str(experiment_root),
            "--reference-timestamp",
            "2026-01-12T09:00:00+00:00",
        ],
    )
    assert experiment.exit_code == 0
    experiment_dir = next(experiment_root.iterdir())
    assert "Quality-gate status: passed" in experiment.output
    assert (
        runner.invoke(
            app,
            ["retrieval-remediation-validate", "--experiment-dir", str(experiment_dir)],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["retrieval-abstention-summary", "--experiment-dir", str(experiment_dir)]
        ).exit_code
        == 0
    )

    comparison_root = tmp_path / "comparison"
    comparison = runner.invoke(
        app,
        [
            "retrieval-remediation-compare",
            "--benchmark-dir",
            str(benchmark),
            "--configuration-registry",
            REGISTRY,
            "--output-root",
            str(comparison_root),
            "--reference-timestamp",
            "2026-01-12T09:00:00+00:00",
        ],
    )
    assert comparison.exit_code == 0
    comparison_dir = next(
        path for path in comparison_root.iterdir() if path.name.startswith("REMCOMP-")
    )
    assert (
        runner.invoke(
            app,
            ["retrieval-remediation-compare-validate", "--comparison-dir", str(comparison_dir)],
        ).exit_code
        == 0
    )
    approval = runner.invoke(
        app,
        ["retrieval-remediation-approval", "--comparison-dir", str(comparison_dir)],
    )
    assert approval.exit_code == 0
    assert "Approved for future RAG prototype: true" in approval.output
