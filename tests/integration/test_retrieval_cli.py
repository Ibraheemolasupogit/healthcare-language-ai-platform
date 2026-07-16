from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app

PREPROCESSING_FIXTURE = "tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc"
EXTRACTION_FIXTURE = "tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d"
QUERY_FIXTURE = "tests/fixtures/retrieval/queries/retrieval_queries.jsonl"
JUDGMENT_FIXTURE = "tests/fixtures/retrieval/queries/relevance_judgments.jsonl"
INDEX_RUN_ID = "IDX-364c8b97f9ad74ecea7444a9"
HYBRID_RUN_ID = "RET-864c03959a1c33a50926b296"
HYBRID_EVAL_ID = "RETEVAL-7ca00cad930651cbf7a6881b"


def test_retrieval_cli_run_validate_summary_and_plans(runner: CliRunner, tmp_path: Path) -> None:
    query_dir = tmp_path / "queries"
    query_result = runner.invoke(
        app,
        [
            "retrieval-query-fixtures",
            "--preprocessing-dir",
            PREPROCESSING_FIXTURE,
            "--output-dir",
            str(query_dir),
        ],
    )
    assert query_result.exit_code == 0
    assert len((query_dir / "retrieval_queries.jsonl").read_text().splitlines()) == 31

    index_root = tmp_path / "indexes"
    index_result = runner.invoke(
        app,
        [
            "index-build",
            "--preprocessing-dir",
            PREPROCESSING_FIXTURE,
            "--extraction-dir",
            EXTRACTION_FIXTURE,
            "--output-root",
            str(index_root),
            "--unit-type",
            "all",
            "--embedding-provider",
            "deterministic_hash",
            "--reference-timestamp",
            "2026-01-06T09:00:00+00:00",
            "--overwrite-policy",
            "force_replace",
        ],
    )
    assert index_result.exit_code == 0
    index_dir = index_root / INDEX_RUN_ID
    validation = runner.invoke(app, ["index-validate", "--index-dir", str(index_dir)])
    assert validation.exit_code == 0
    summary = runner.invoke(app, ["index-summary", "--index-dir", str(index_dir)])
    assert summary.exit_code == 0
    assert "Retrieval-unit count: 153" in summary.output

    run_root = tmp_path / "runs"
    run_result = runner.invoke(
        app,
        [
            "retrieve-run",
            "--index-dir",
            str(index_dir),
            "--query-set",
            QUERY_FIXTURE,
            "--output-root",
            str(run_root),
            "--strategy",
            "hybrid",
            "--top-k",
            "5",
            "--reference-timestamp",
            "2026-01-07T09:00:00+00:00",
            "--overwrite-policy",
            "force_replace",
        ],
    )
    assert run_result.exit_code == 0
    retrieval_dir = run_root / HYBRID_RUN_ID
    run_validation = runner.invoke(
        app, ["retrieve-validate", "--retrieval-dir", str(retrieval_dir)]
    )
    assert run_validation.exit_code == 0
    run_summary = runner.invoke(app, ["retrieve-summary", "--retrieval-dir", str(retrieval_dir)])
    assert run_summary.exit_code == 0
    assert "Strategy: hybrid" in run_summary.output

    eval_root = tmp_path / "evaluations"
    eval_result = runner.invoke(
        app,
        [
            "retrieval-evaluate",
            "--retrieval-dir",
            str(retrieval_dir),
            "--relevance-judgments",
            JUDGMENT_FIXTURE,
            "--output-root",
            str(eval_root),
            "--k-values",
            "1,3,5,10",
            "--reference-timestamp",
            "2026-01-08T09:00:00+00:00",
            "--overwrite-policy",
            "force_replace",
        ],
    )
    assert eval_result.exit_code == 0
    evaluation_dir = eval_root / HYBRID_EVAL_ID
    eval_validation = runner.invoke(
        app, ["retrieval-evaluate-validate", "--evaluation-dir", str(evaluation_dir)]
    )
    assert eval_validation.exit_code == 0
    eval_summary = runner.invoke(
        app, ["retrieval-evaluate-summary", "--evaluation-dir", str(evaluation_dir)]
    )
    assert eval_summary.exit_code == 0
    assert "Hit Rate@5: 0.451613" in eval_summary.output

    vector_plan = runner.invoke(
        app, ["vector-search-plan", "--evaluation-dir", str(evaluation_dir)]
    )
    assert vector_plan.exit_code == 0
    assert "Connection attempted: false" in vector_plan.output
    mlflow_plan = runner.invoke(
        app, ["retrieval-mlflow-plan", "--evaluation-dir", str(evaluation_dir)]
    )
    assert mlflow_plan.exit_code == 0
    assert "Connection attempted: false" in mlflow_plan.output


def test_retrieval_cli_invalid_source_returns_non_zero(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "index-build",
            "--preprocessing-dir",
            str(tmp_path / "missing-preprocessing"),
            "--extraction-dir",
            EXTRACTION_FIXTURE,
            "--output-root",
            str(tmp_path / "indexes"),
        ],
    )
    assert result.exit_code != 0
