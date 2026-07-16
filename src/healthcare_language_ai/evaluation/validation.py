"""Validation for persisted evaluation evidence."""

from __future__ import annotations

import csv
from pathlib import Path

from healthcare_language_ai.evaluation.contracts import (
    BaselineModelCard,
    EvaluationManifest,
    EvaluationReconciliationReport,
    MLflowExperimentPlan,
)
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_evaluation_dir(evaluation_dir: Path) -> list[str]:
    failures: list[str] = []
    manifest = EvaluationManifest.model_validate(
        read_json(evaluation_dir / "evaluation_manifest.json")
    )
    reconciliation = EvaluationReconciliationReport.model_validate(
        read_json(evaluation_dir / "evaluation_reconciliation.json")
    )
    card = BaselineModelCard.model_validate(read_json(evaluation_dir / "baseline_model_card.json"))
    mlflow_plan = MLflowExperimentPlan.model_validate(
        read_json(evaluation_dir / "mlflow_experiment_plan.json")
    )
    for file_name, expected_checksum in manifest.output_file_checksums.items():
        path = evaluation_dir / file_name
        if not path.exists():
            failures.append(f"missing output file: {file_name}")
        elif sha256_file(path) != expected_checksum:
            failures.append(f"checksum mismatch: {file_name}")
    if reconciliation.overall_status != manifest.reconciliation_status:
        failures.append("reconciliation status mismatch")
    if reconciliation.overall_status == "failed":
        failures.append("evaluation reconciliation failed")
    if mlflow_plan.connection_attempted or mlflow_plan.execution_permitted:
        failures.append("MLflow plan is not dry-run safe")
    if mlflow_plan.evaluation_run_id != manifest.evaluation_run_id:
        failures.append("MLflow plan evaluation run mismatch")
    if card.metrics.get("entity_micro_f1") != manifest.micro_f1:
        failures.append("model-card entity micro F1 mismatch")
    if len(_csv_rows(evaluation_dir / "error_analysis.csv")) != manifest.error_count:
        failures.append("error-analysis count mismatch")
    confusion_total = sum(
        int(row["count"])
        for row in _csv_rows(evaluation_dir / "document_type_confusion_matrix.csv")
    )
    if confusion_total != manifest.evaluated_document_count:
        failures.append("confusion-matrix total mismatch")
    return failures
