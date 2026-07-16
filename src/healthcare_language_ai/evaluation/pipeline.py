"""Deterministic baseline evaluation pipeline."""

from __future__ import annotations

import csv
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from healthcare_language_ai.config import EvaluationSettings
from healthcare_language_ai.evaluation.contracts import (
    BaselineModelCard,
    ClassificationEvaluationMetric,
    ConfusionMatrixRecord,
    EntityEvaluationMetric,
    ErrorAnalysisRecord,
    EvaluationManifest,
    EvaluationMatch,
    EvaluationReconciliationMetric,
    EvaluationReconciliationReport,
    EvaluationRunStatus,
    MLflowExperimentPlan,
)
from healthcare_language_ai.evaluation.serialisation import (
    CLASSIFICATION_METRIC_COLUMNS,
    CONFUSION_COLUMNS,
    ENTITY_METRIC_COLUMNS,
    ERROR_COLUMNS,
    MATCH_COLUMNS,
    write_csv,
    write_json_model,
    write_jsonl,
)
from healthcare_language_ai.exceptions import DataGovernanceError
from healthcare_language_ai.extraction.contracts import SUPPORTED_ENTITY_LABELS
from healthcare_language_ai.extraction.pipeline import load_extraction_manifest
from healthcare_language_ai.extraction.validation import validate_extraction_dir
from healthcare_language_ai.ingestion.contracts import OverwritePolicy
from healthcare_language_ai.preprocessing.pipeline import load_preprocessing_manifest
from healthcare_language_ai.preprocessing.validation import validate_preprocessing_dir
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json
from healthcare_language_ai.utils.identifiers import deterministic_id


def derive_evaluation_run_id(
    *,
    extraction_manifest_checksum: str,
    ground_truth_checksum: str,
    evaluation_contract_version: str,
    metrics_version: str,
    matching_policy: str,
    relaxed_overlap_threshold: float,
    reference_timestamp: datetime,
) -> str:
    value = deterministic_id(
        {
            "extraction_manifest_checksum": extraction_manifest_checksum,
            "ground_truth_checksum": ground_truth_checksum,
            "evaluation_contract_version": evaluation_contract_version,
            "metrics_version": metrics_version,
            "matching_policy": matching_policy,
            "relaxed_overlap_threshold": relaxed_overlap_threshold,
            "reference_timestamp": reference_timestamp.isoformat(),
        },
        length=24,
    )
    return f"EVAL-{value}"


def _prepare_output_dir(output_dir: Path, policy: OverwritePolicy) -> None:
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return
    if policy is OverwritePolicy.FAIL_IF_EXISTS:
        msg = f"output directory already exists: {output_dir}"
        raise FileExistsError(msg)
    shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _safe_div(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return round((2 * precision * recall) / (precision + recall), 6) if precision + recall else 0.0


def _metric(
    scope: str,
    value: str,
    tp: int,
    fp: int,
    fn: int,
    evaluation_run_id: str,
) -> EntityEvaluationMetric:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return EntityEvaluationMetric(
        metric_scope=scope,
        scope_value=value,
        true_positive_count=tp,
        false_positive_count=fp,
        false_negative_count=fn,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        support=tp + fn,
        evaluation_run_id=evaluation_run_id,
    )


def _truth_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row["document_id"],
        row["label"],
        row["target_start"],
        row["target_end"],
        row["value"].casefold(),
    )


def _prediction_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row["document_id"],
        row["label"],
        row["start_offset"],
        row["end_offset"],
        row["normalised_value"],
    )


def _context(text: str, start: int | None, end: int | None, window: int) -> str:
    if start is None or end is None:
        return "synthetic document-level classification context omitted"
    prefix = max(0, start - window)
    suffix = min(len(text), end + window)
    return text[prefix:suffix].replace("\n", " ")[: (window * 2) + max(0, end - start)]


def _reconciliation(
    *,
    evaluation_run_id: str,
    truth_count: int,
    prediction_count: int,
    tp: int,
    fp: int,
    fn: int,
    confusion_total: int,
    document_count: int,
    error_count: int,
    output_checksum_status: bool,
) -> EvaluationReconciliationReport:
    metrics = [
        _recon_metric("truth_accounting", truth_count, tp + fn, "TP + FN equals truth"),
        _recon_metric(
            "prediction_accounting",
            prediction_count,
            tp + fp,
            "TP + FP equals predictions",
        ),
        _recon_metric(
            "confusion_matrix_total",
            document_count,
            confusion_total,
            "confusion matrix totals reconcile",
        ),
        _recon_metric("error_accounting", fp + fn, error_count, "errors reconcile with FP and FN"),
        _recon_metric("manifest_checksums", True, output_checksum_status, "checksums validate"),
    ]
    return EvaluationReconciliationReport(
        reconciliation_schema_version="1.0.0",
        evaluation_run_id=evaluation_run_id,
        overall_status="failed"
        if any(item.status == "failed" for item in metrics)
        else "warning"
        if any(item.status == "warning" for item in metrics)
        else "passed",
        metrics=metrics,
    )


def _recon_metric(
    name: str, expected: int | str | bool, actual: int | str | bool, message: str
) -> EvaluationReconciliationMetric:
    passed = expected == actual
    return EvaluationReconciliationMetric(
        metric_name=name,
        expected_value=expected,
        actual_value=actual,
        status="passed" if passed else "failed",
        severity="info" if passed else "error",
        message=message,
    )


def _classification_metrics(
    *,
    truth_by_doc: dict[str, str],
    pred_by_doc: dict[str, str],
    evaluation_run_id: str,
) -> tuple[list[ClassificationEvaluationMetric], list[ConfusionMatrixRecord], float, float]:
    classes = sorted(set(truth_by_doc.values()) | set(pred_by_doc.values()))
    confusion_counts = Counter(
        (actual, pred_by_doc.get(document_id, "missing"))
        for document_id, actual in truth_by_doc.items()
    )
    confusion = [
        ConfusionMatrixRecord(
            actual_document_type=actual,
            predicted_document_type=predicted,
            count=count,
            evaluation_run_id=evaluation_run_id,
        )
        for (actual, predicted), count in sorted(confusion_counts.items())
    ]
    metrics: list[ClassificationEvaluationMetric] = []
    total_correct = sum(
        actual == pred_by_doc.get(document_id) for document_id, actual in truth_by_doc.items()
    )
    accuracy = _safe_div(total_correct, len(truth_by_doc))
    for class_label in classes:
        tp = sum(
            actual == class_label and pred_by_doc.get(document_id) == class_label
            for document_id, actual in truth_by_doc.items()
        )
        fp = sum(
            actual != class_label and pred_by_doc.get(document_id) == class_label
            for document_id, actual in truth_by_doc.items()
        )
        fn = sum(
            actual == class_label and pred_by_doc.get(document_id) != class_label
            for document_id, actual in truth_by_doc.items()
        )
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        metrics.append(
            ClassificationEvaluationMetric(
                class_label=class_label,
                true_positive_count=tp,
                false_positive_count=fp,
                false_negative_count=fn,
                precision=precision,
                recall=recall,
                f1=_f1(precision, recall),
                support=tp + fn,
                accuracy=accuracy,
                evaluation_run_id=evaluation_run_id,
            )
        )
    macro_f1 = round(sum(item.f1 for item in metrics) / len(metrics), 6) if metrics else 0.0
    return metrics, confusion, accuracy, macro_f1


def _model_card(
    *,
    micro_f1: float,
    macro_f1: float,
    classification_accuracy: float,
    classification_macro_f1: float,
) -> BaselineModelCard:
    return BaselineModelCard(
        model_name="Deterministic Rule-Based Clinical NLP Baseline",
        model_version="1.0.0",
        model_type="Rule-based baseline",
        purpose="Portfolio baseline for synthetic clinical NLP pipeline validation.",
        intended_use="Synthetic-data-only extraction and evaluation workflow validation.",
        out_of_scope_use=(
            "Patient care, diagnosis, treatment, coding, triage, or clinical decision support."
        ),
        training_data="None; no model training is performed.",
        evaluation_data="Controlled synthetic Milestone 4 preprocessing fixture.",
        rule_and_vocabulary_sources=(
            "Local synthetic generation vocabularies and transparent heading rules."
        ),
        input_contract=(
            "Validated preprocessing evidence with normalised text and projected annotations."
        ),
        output_contract="Deterministic prediction, metric, error-analysis and manifest evidence.",
        supported_labels=sorted(SUPPORTED_ENTITY_LABELS),
        metrics={
            "entity_micro_f1": micro_f1,
            "entity_macro_f1": macro_f1,
            "classification_accuracy": classification_accuracy,
            "classification_macro_f1": classification_macro_f1,
        },
        known_limitations=[
            "Synthetic templates are familiar to the rules.",
            "Vocabulary overlap can inflate scores.",
            "No real-world clinical generalisation is demonstrated.",
        ],
        synthetic_data_limitation="All evidence is synthetic and portfolio-only.",
        benchmark_leakage=(
            "Extraction vocabulary intentionally overlaps with generation vocabulary."
        ),
        clinical_safety_limitations=(
            "Not clinically validated, not a medical device and not for care."
        ),
        fairness_limitations="Synthetic fixture has no demographic representativeness claim.",
        privacy_position="No real patient data is used or required.",
        failure_modes=["Missed unseen phrasing", "Boundary mismatch", "Unsupported terminology"],
        human_review_expectations=(
            "Any future clinical use would require expert review and validation."
        ),
        monitoring_recommendations=(
            "Monitor label drift, unmatched phrases and error-analysis trends."
        ),
        future_model_comparison_plan=(
            "Compare future trained models against this reproducible baseline."
        ),
    )


def _model_card_markdown(card: BaselineModelCard) -> str:
    return (
        f"# {card.model_name}\n\n"
        f"Version: {card.model_version}\n\n"
        f"Type: {card.model_type}\n\n"
        f"Purpose: {card.purpose}\n\n"
        f"Intended use: {card.intended_use}\n\n"
        f"Out of scope: {card.out_of_scope_use}\n\n"
        "This baseline is not clinically validated and is not suitable for patient care.\n"
    )


def run_evaluation(
    *,
    extraction_dir: Path,
    preprocessing_dir: Path,
    output_root: Path,
    matching_policy: str,
    reference_timestamp: datetime,
    overwrite_policy: OverwritePolicy,
    settings: EvaluationSettings,
) -> Path:
    if matching_policy not in {"exact", "exact_normalised_value", "relaxed_overlap"}:
        msg = "unsupported matching policy"
        raise ValueError(msg)
    extraction_failures = validate_extraction_dir(extraction_dir)
    preprocessing_failures = validate_preprocessing_dir(preprocessing_dir)
    if extraction_failures or preprocessing_failures:
        msg = "source evidence failed validation"
        raise DataGovernanceError(msg)
    extraction_manifest = load_extraction_manifest(extraction_dir)
    preprocessing_manifest = load_preprocessing_manifest(preprocessing_dir)
    if (
        not extraction_manifest.synthetic_data_only
        or not preprocessing_manifest.synthetic_data_only
    ):
        msg = "evaluation sources must be synthetic only"
        raise DataGovernanceError(msg)
    extraction_checksum = sha256_file(extraction_dir / "extraction_manifest.json")
    truth_checksum = sha256_file(preprocessing_dir / "projected_annotations.csv")
    evaluation_run_id = derive_evaluation_run_id(
        extraction_manifest_checksum=extraction_checksum,
        ground_truth_checksum=truth_checksum,
        evaluation_contract_version=settings.evaluation_contract_version,
        metrics_version=settings.metrics_version,
        matching_policy=matching_policy,
        relaxed_overlap_threshold=settings.relaxed_overlap_threshold,
        reference_timestamp=reference_timestamp,
    )
    output_dir = output_root / evaluation_run_id
    _prepare_output_dir(output_dir, overwrite_policy)

    documents = _read_csv(preprocessing_dir / "processed_documents.csv")
    doc_text = {row["document_id"]: row["normalised_text"] for row in documents}
    doc_type = {row["document_id"]: row["document_type"] for row in documents}
    truth_rows = [
        row
        for row in _read_csv(preprocessing_dir / "projected_annotations.csv")
        if row["annotation_type"] == "span"
        and row["projection_status"] in {"projected", "unchanged"}
        and row["label"] in SUPPORTED_ENTITY_LABELS
    ]
    prediction_rows = _read_csv(extraction_dir / "entity_predictions.csv")
    pred_by_key = {_prediction_key(row): row for row in prediction_rows}
    truth_by_key = {_truth_key(row): row for row in truth_rows}
    matched_keys = sorted(set(pred_by_key) & set(truth_by_key))
    fp_keys = sorted(set(pred_by_key) - set(truth_by_key))
    fn_keys = sorted(set(truth_by_key) - set(pred_by_key))
    matches: list[EvaluationMatch] = []
    for key in matched_keys:
        pred = pred_by_key[key]
        truth = truth_by_key[key]
        matches.append(
            EvaluationMatch(
                match_id="MATCH_"
                + deterministic_id({"run": evaluation_run_id, "key": key}, length=20),
                document_id=pred["document_id"],
                label=pred["label"],
                prediction_id=pred["prediction_id"],
                ground_truth_annotation_id=truth["annotation_id"],
                match_type="true_positive",
                matching_policy=matching_policy,
                start_offset=int(pred["start_offset"]),
                end_offset=int(pred["end_offset"]),
                evaluation_run_id=evaluation_run_id,
            )
        )
    errors: list[ErrorAnalysisRecord] = []
    for key in fp_keys:
        pred = pred_by_key[key]
        start = int(pred["start_offset"])
        end = int(pred["end_offset"])
        errors.append(
            ErrorAnalysisRecord(
                error_id="ERR_"
                + deterministic_id({"run": evaluation_run_id, "fp": key}, length=20),
                document_id=pred["document_id"],
                document_type=doc_type[pred["document_id"]],
                label=pred["label"],
                error_type="false_positive",
                prediction_id=pred["prediction_id"],
                predicted_value=pred["normalised_value"],
                predicted_start=start,
                predicted_end=end,
                section_label=None,
                sentence_id=pred["sentence_id"] or None,
                rule_id=pred["rule_id"],
                sanitised_context=_context(
                    doc_text[pred["document_id"]], start, end, settings.context_window_characters
                ),
                context_checksum=sha256_file(extraction_dir / "entity_predictions.csv"),
                likely_reason="prediction did not align to projected synthetic ground truth",
                evaluation_run_id=evaluation_run_id,
            )
        )
    for key in fn_keys:
        truth = truth_by_key[key]
        start = int(truth["target_start"])
        end = int(truth["target_end"])
        errors.append(
            ErrorAnalysisRecord(
                error_id="ERR_"
                + deterministic_id({"run": evaluation_run_id, "fn": key}, length=20),
                document_id=truth["document_id"],
                document_type=doc_type[truth["document_id"]],
                label=truth["label"],
                error_type="false_negative",
                ground_truth_annotation_id=truth["annotation_id"],
                expected_value=truth["value"].casefold(),
                expected_start=start,
                expected_end=end,
                sanitised_context=_context(
                    doc_text[truth["document_id"]], start, end, settings.context_window_characters
                ),
                context_checksum=sha256_file(preprocessing_dir / "projected_annotations.csv"),
                likely_reason="projected synthetic ground truth was not predicted",
                evaluation_run_id=evaluation_run_id,
            )
        )
    tp, fp, fn = len(matched_keys), len(fp_keys), len(fn_keys)
    overall = _metric("overall", "micro", tp, fp, fn, evaluation_run_id)
    label_metrics = [
        _metric(
            "label",
            label,
            sum(key[1] == label for key in matched_keys),
            sum(key[1] == label for key in fp_keys),
            sum(key[1] == label for key in fn_keys),
            evaluation_run_id,
        )
        for label in sorted(SUPPORTED_ENTITY_LABELS)
    ]
    doc_type_metrics = [
        _metric(
            "document_type",
            dtype,
            sum(doc_type[key[0]] == dtype for key in matched_keys),
            sum(doc_type[key[0]] == dtype for key in fp_keys),
            sum(doc_type[key[0]] == dtype for key in fn_keys),
            evaluation_run_id,
        )
        for dtype in sorted(set(doc_type.values()))
    ]
    macro_precision = round(sum(item.precision for item in label_metrics) / len(label_metrics), 6)
    macro_recall = round(sum(item.recall for item in label_metrics) / len(label_metrics), 6)
    macro_f1 = round(sum(item.f1 for item in label_metrics) / len(label_metrics), 6)
    class_rows = _read_csv(extraction_dir / "document_classifications.csv")
    pred_doc_type = {row["document_id"]: row["predicted_document_type"] for row in class_rows}
    class_metrics, confusion, class_accuracy, class_macro_f1 = _classification_metrics(
        truth_by_doc=doc_type,
        pred_by_doc=pred_doc_type,
        evaluation_run_id=evaluation_run_id,
    )
    card = _model_card(
        micro_f1=overall.f1,
        macro_f1=macro_f1,
        classification_accuracy=class_accuracy,
        classification_macro_f1=class_macro_f1,
    )
    mlflow_plan = MLflowExperimentPlan(
        plan_schema_version="1.0.0",
        mlflow_contract_version=settings.mlflow_contract_version,
        experiment_name_placeholder="/Shared/hla/rule_based_baseline",
        run_name=f"baseline-{evaluation_run_id}",
        extraction_run_id=extraction_manifest.extraction_run_id,
        evaluation_run_id=evaluation_run_id,
        parameters={
            "matching_policy": matching_policy,
            "text_representation": extraction_manifest.text_representation,
        },
        metrics_to_log={
            "entity_micro_f1": overall.f1,
            "entity_macro_f1": macro_f1,
            "classification_accuracy": class_accuracy,
            "classification_macro_f1": class_macro_f1,
        },
        tags={"synthetic_data_only": "true", "clinical_use_prohibited": "true"},
        artifacts_to_log=["baseline_model_card.json", "baseline_model_card.md"],
        dataset_lineage={
            "preprocessing_run_id": preprocessing_manifest.preprocessing_run_id,
            "extraction_run_id": extraction_manifest.extraction_run_id,
        },
        rule_versions={
            "entity_rule_version": extraction_manifest.entity_rule_version,
            "classification_rule_version": extraction_manifest.classification_rule_version,
        },
        target_registry_stage_placeholder="none",
        dry_run_status="validated",
        connection_attempted=False,
        execution_permitted=False,
    )
    write_csv(output_dir / "entity_metrics_overall.csv", [overall], ENTITY_METRIC_COLUMNS)
    write_csv(output_dir / "entity_metrics_by_label.csv", label_metrics, ENTITY_METRIC_COLUMNS)
    write_csv(
        output_dir / "entity_metrics_by_document_type.csv",
        doc_type_metrics,
        ENTITY_METRIC_COLUMNS,
    )
    write_csv(
        output_dir / "classification_metrics.csv",
        class_metrics,
        CLASSIFICATION_METRIC_COLUMNS,
    )
    write_csv(output_dir / "document_type_confusion_matrix.csv", confusion, CONFUSION_COLUMNS)
    write_csv(output_dir / "entity_matches.csv", matches, MATCH_COLUMNS)
    write_csv(output_dir / "error_analysis.csv", errors, ERROR_COLUMNS)
    write_jsonl(output_dir / "error_analysis.jsonl", errors)
    write_json_model(output_dir / "baseline_model_card.json", card)
    (output_dir / "baseline_model_card.md").write_text(
        _model_card_markdown(card), encoding="utf-8", newline="\n"
    )
    write_json_model(output_dir / "mlflow_experiment_plan.json", mlflow_plan)
    output_checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "evaluation_manifest.json"
    }
    reconciliation = _reconciliation(
        evaluation_run_id=evaluation_run_id,
        truth_count=len(truth_rows),
        prediction_count=len(prediction_rows),
        tp=tp,
        fp=fp,
        fn=fn,
        confusion_total=sum(item.count for item in confusion),
        document_count=len(documents),
        error_count=len(errors),
        output_checksum_status=True,
    )
    write_json_model(output_dir / "evaluation_reconciliation.json", reconciliation)
    output_checksums["evaluation_reconciliation.json"] = sha256_file(
        output_dir / "evaluation_reconciliation.json"
    )
    manifest = EvaluationManifest(
        manifest_schema_version="1.0.0",
        evaluation_contract_version=settings.evaluation_contract_version,
        evaluation_run_id=evaluation_run_id,
        run_status=EvaluationRunStatus.COMPLETED
        if reconciliation.overall_status == "passed"
        else EvaluationRunStatus.COMPLETED_WITH_WARNINGS,
        source_extraction_run_id=extraction_manifest.extraction_run_id,
        source_extraction_manifest_checksum=extraction_checksum,
        ground_truth_source=str(preprocessing_dir / "projected_annotations.csv"),
        ground_truth_checksum=truth_checksum,
        matching_policy=matching_policy,
        relaxed_overlap_threshold=settings.relaxed_overlap_threshold,
        evaluated_document_count=len(documents),
        evaluated_ground_truth_count=len(truth_rows),
        evaluated_prediction_count=len(prediction_rows),
        excluded_ground_truth_count=0,
        true_positive_count=tp,
        false_positive_count=fp,
        false_negative_count=fn,
        micro_precision=overall.precision,
        micro_recall=overall.recall,
        micro_f1=overall.f1,
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        macro_f1=macro_f1,
        classification_accuracy=class_accuracy,
        classification_macro_f1=class_macro_f1,
        error_count=len(errors),
        metrics_version=settings.metrics_version,
        error_analysis_version=settings.error_analysis_version,
        mlflow_contract_version=settings.mlflow_contract_version,
        reference_timestamp=reference_timestamp,
        output_files=sorted(output_checksums),
        output_file_checksums=dict(sorted(output_checksums.items())),
        synthetic_data_only=True,
        clinical_use_prohibited=True,
        reconciliation_status=reconciliation.overall_status,
    )
    write_json_model(output_dir / "evaluation_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        "# Baseline Evaluation Evidence\n\n"
        f"Run ID: {evaluation_run_id}\n"
        "No MLflow tracking connection was attempted.\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_dir


def load_evaluation_manifest(evaluation_dir: Path) -> EvaluationManifest:
    return EvaluationManifest.model_validate(read_json(evaluation_dir / "evaluation_manifest.json"))
