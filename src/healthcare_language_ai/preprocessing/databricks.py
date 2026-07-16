"""Databricks-style target-state contracts and dry-run plans."""

from __future__ import annotations

from healthcare_language_ai.preprocessing.contracts import (
    DatabricksColumnContract,
    DatabricksJobContract,
    DatabricksNotebookContract,
    DatabricksPipelinePlan,
    DatabricksTableContract,
)

SUPPORTED_SPARK_TYPES = {
    "STRING",
    "LONG",
    "DOUBLE",
    "BOOLEAN",
    "TIMESTAMP",
    "ARRAY",
    "MAP",
    "STRUCT",
}


def _col(
    name: str, typ: str, source: str, desc: str, *, nullable: bool = False
) -> DatabricksColumnContract:
    return DatabricksColumnContract(
        column_name=name,
        spark_type=typ,
        nullable=nullable,
        natural_key=name.endswith("_id"),
        source_field=source,
        description=desc,
        governance_classification="synthetic",
        partition_recommendation="document_type" if name == "document_type" else None,
    )


def table_contracts() -> list[DatabricksTableContract]:
    doc_cols = [
        _col("document_id", "STRING", "document_id", "Synthetic document ID"),
        _col("document_type", "STRING", "document_type", "Document type"),
        _col("normalised_text", "STRING", "normalised_text", "Normalised text"),
        _col("preprocessing_run_id", "STRING", "preprocessing_run_id", "Run ID"),
    ]
    sent_cols = [
        _col("sentence_id", "STRING", "sentence_id", "Sentence ID"),
        _col("document_id", "STRING", "document_id", "Document ID"),
        _col("sentence_text", "STRING", "sentence_text", "Sentence text"),
        _col("token_count", "LONG", "token_count", "Lexical token count"),
    ]
    quality_cols = [
        _col("document_id", "STRING", "document_id", "Document ID"),
        _col("check_name", "STRING", "check_name", "Quality check"),
        _col("status", "STRING", "status", "Quality status"),
    ]
    return [
        DatabricksTableContract(
            table_name="bronze_clinical_documents",
            medallion_layer="bronze",
            description="Canonical ingested documents",
            columns=doc_cols,
        ),
        DatabricksTableContract(
            table_name="bronze_document_annotations",
            medallion_layer="bronze",
            description="Canonical annotations",
            columns=sent_cols,
        ),
        DatabricksTableContract(
            table_name="silver_processed_documents",
            medallion_layer="silver",
            description="Processed documents",
            columns=doc_cols,
        ),
        DatabricksTableContract(
            table_name="silver_document_sections",
            medallion_layer="silver",
            description="Parsed sections",
            columns=doc_cols,
        ),
        DatabricksTableContract(
            table_name="silver_document_sentences",
            medallion_layer="silver",
            description="Segmented sentences",
            columns=sent_cols,
        ),
        DatabricksTableContract(
            table_name="silver_projected_annotations",
            medallion_layer="silver",
            description="Projected annotations",
            columns=sent_cols,
        ),
        DatabricksTableContract(
            table_name="silver_document_quality",
            medallion_layer="silver",
            description="Quality metrics",
            columns=quality_cols,
        ),
        DatabricksTableContract(
            table_name="gold_preprocessing_summary",
            medallion_layer="gold",
            description="Run summaries",
            columns=quality_cols,
        ),
        DatabricksTableContract(
            table_name="gold_document_type_metrics",
            medallion_layer="gold",
            description="Document type metrics",
            columns=quality_cols,
        ),
        DatabricksTableContract(
            table_name="gold_quality_metrics",
            medallion_layer="gold",
            description="Quality metrics",
            columns=quality_cols,
        ),
    ]


def notebook_sequence() -> list[DatabricksNotebookContract]:
    names = [
        "01_validate_ingestion_source",
        "02_preprocess_documents",
        "03_parse_sections",
        "04_segment_sentences",
        "05_project_annotations",
        "06_quality_and_reconciliation",
        "07_publish_silver_gold",
    ]
    return [
        DatabricksNotebookContract(
            notebook_name=name,
            purpose=f"Target-state contract for {name}",
            inputs=["local preprocessing evidence"],
            outputs=["Delta table contract references"],
            validation_gates=["schema", "counts", "governance"],
        )
        for name in names
    ]


def build_plan(
    *,
    run_id: str,
    source_files: list[str],
    checksums: dict[str, str],
    document_count: int,
    sentence_count: int,
    quality_status: str,
) -> DatabricksPipelinePlan:
    return DatabricksPipelinePlan(
        plan_schema_version="1.0.0",
        preprocessing_run_id=run_id,
        source_files=source_files,
        target_medallion_layers=["bronze", "silver", "gold"],
        target_table_contracts=table_contracts(),
        notebook_task_sequence=notebook_sequence(),
        job_contract=DatabricksJobContract(
            job_name="hla-preprocessing-target-state",
            task_order=[item.notebook_name for item in notebook_sequence()],
            retry_policy="reference-only: max 1 retry",
            timeout_policy="reference-only: 30 minutes per task",
            execution_permitted=False,
        ),
        expected_record_counts={
            "processed_documents": document_count,
            "processed_sentences": sentence_count,
        },
        expected_checksums=checksums,
        quality_gates={"quality_status": quality_status, "schema_validation": "required"},
        required_target_state_permissions=["USE CATALOG", "USE SCHEMA", "CREATE TABLE"],
        dry_run_status="validated",
        connection_attempted=False,
        execution_permitted=False,
    )


def validate_table_contracts(contracts: list[DatabricksTableContract]) -> bool:
    return all(
        column.spark_type in SUPPORTED_SPARK_TYPES
        for table in contracts
        for column in table.columns
    )
