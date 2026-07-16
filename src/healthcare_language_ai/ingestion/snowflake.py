"""Snowflake-oriented contracts and dry-run load plans."""

from __future__ import annotations

from pathlib import Path

from healthcare_language_ai.ingestion.contracts import (
    SnowflakeColumnContract,
    SnowflakeLoadPlan,
    SnowflakeTableContract,
)

SUPPORTED_TYPES = {"VARCHAR", "NUMBER", "BOOLEAN", "TIMESTAMP_TZ", "VARIANT"}


def _col(name: str, typ: str, nullable: bool, source: str, desc: str) -> SnowflakeColumnContract:
    return SnowflakeColumnContract(
        column_name=name,
        snowflake_type=typ,
        nullable=nullable,
        key_role="natural_key" if name.endswith("_ID") else None,
        description=desc,
        source_field=source,
        governance_classification="synthetic",
    )


def table_contracts(
    database: str, raw_schema: str, staging_schema: str, governance_schema: str
) -> list[SnowflakeTableContract]:
    raw_ns = f"{database}.{raw_schema}"
    stg_ns = f"{database}.{staging_schema}"
    gov_ns = f"{database}.{governance_schema}"
    doc_cols = [
        _col("DOCUMENT_ID", "VARCHAR", False, "document_id", "Synthetic document identifier"),
        _col("DOCUMENT_TYPE", "VARCHAR", False, "document_type", "Synthetic document type"),
        _col("DOCUMENT_TEXT", "VARCHAR", False, "document_text", "Synthetic document text"),
        _col("INGESTION_RUN_ID", "VARCHAR", False, "ingestion_run_id", "Deterministic run ID"),
        _col(
            "INGESTED_AT", "TIMESTAMP_TZ", False, "ingested_at", "Deterministic ingestion timestamp"
        ),
    ]
    ann_cols = [
        _col("ANNOTATION_ID", "VARCHAR", False, "annotation_id", "Deterministic annotation ID"),
        _col("DOCUMENT_ID", "VARCHAR", False, "document_id", "Synthetic document identifier"),
        _col("LABEL", "VARCHAR", False, "label", "Annotation label"),
        _col("START_OFFSET", "NUMBER", True, "start_offset", "Span start offset"),
        _col("END_OFFSET", "NUMBER", True, "end_offset", "Span end offset"),
    ]
    return [
        SnowflakeTableContract(
            table_name="RAW_CLINICAL_DOCUMENTS",
            namespace=raw_ns,
            description="Raw canonical documents",
            columns=doc_cols,
        ),
        SnowflakeTableContract(
            table_name="RAW_DOCUMENT_ANNOTATIONS",
            namespace=raw_ns,
            description="Raw canonical annotations",
            columns=ann_cols,
        ),
        SnowflakeTableContract(
            table_name="STG_CLINICAL_DOCUMENTS",
            namespace=stg_ns,
            description="Validated staging documents",
            columns=doc_cols,
        ),
        SnowflakeTableContract(
            table_name="STG_DOCUMENT_ANNOTATIONS",
            namespace=stg_ns,
            description="Validated staging annotations",
            columns=ann_cols,
        ),
        SnowflakeTableContract(
            table_name="INGESTION_RUNS",
            namespace=gov_ns,
            description="Ingestion run evidence",
            columns=[
                _col("INGESTION_RUN_ID", "VARCHAR", False, "ingestion_run_id", "Run ID"),
                _col("RUN_STATUS", "VARCHAR", False, "run_status", "Run status"),
            ],
        ),
        SnowflakeTableContract(
            table_name="INGESTION_RECONCILIATION",
            namespace=gov_ns,
            description="Reconciliation evidence",
            columns=[
                _col("INGESTION_RUN_ID", "VARCHAR", False, "ingestion_run_id", "Run ID"),
                _col("METRIC_NAME", "VARCHAR", False, "metric_name", "Metric"),
            ],
        ),
        SnowflakeTableContract(
            table_name="QUARANTINED_RECORDS",
            namespace=gov_ns,
            description="Quarantine evidence",
            columns=[
                _col("PAYLOAD_CHECKSUM", "VARCHAR", False, "payload_checksum", "Payload checksum"),
                _col("ERROR_CODE", "VARCHAR", False, "error_code", "Error code"),
            ],
        ),
    ]


def build_load_plan(
    *,
    output_dir: Path,
    target_database: str,
    raw_schema: str,
    staging_schema: str,
    governance_schema: str,
    snowflake_contract_version: str,
    checksums: dict[str, str],
    document_count: int,
    annotation_count: int,
) -> SnowflakeLoadPlan:
    contracts = table_contracts(target_database, raw_schema, staging_schema, governance_schema)
    return SnowflakeLoadPlan(
        plan_schema_version="1.0.0",
        snowflake_contract_version=snowflake_contract_version,
        target_database=target_database,
        target_schemas=[raw_schema, staging_schema, governance_schema],
        target_tables=contracts,
        input_files=[
            "canonical_clinical_documents.csv",
            "canonical_document_annotations.csv",
            "canonical_clinical_documents.parquet",
            "canonical_document_annotations.parquet",
        ],
        input_format={
            "csv": "UTF-8, LF, header row, RFC quoting, empty string as null reference",
            "parquet": "Parquet with zstd compression unless configured otherwise",
            "stage": "@HLA_LOCAL_REFERENCE_STAGE (non-functional reference)",
        },
        expected_row_counts={
            "RAW_CLINICAL_DOCUMENTS": document_count,
            "RAW_DOCUMENT_ANNOTATIONS": annotation_count,
        },
        expected_checksums=checksums,
        column_mappings={
            "RAW_CLINICAL_DOCUMENTS": {
                "DOCUMENT_ID": "document_id",
                "DOCUMENT_TEXT": "document_text",
            },
            "RAW_DOCUMENT_ANNOTATIONS": {"ANNOTATION_ID": "annotation_id", "LABEL": "label"},
        },
        copy_into_reference_statements=[
            (
                "COPY INTO HEALTHCARE_LANGUAGE_AI.RAW.RAW_CLINICAL_DOCUMENTS "
                "FROM @HLA_LOCAL_REFERENCE_STAGE "
                "FILE_FORMAT=(FORMAT_NAME=HLA_CANONICAL_CSV);"
            ),
            (
                "COPY INTO HEALTHCARE_LANGUAGE_AI.RAW.RAW_DOCUMENT_ANNOTATIONS "
                "FROM @HLA_LOCAL_REFERENCE_STAGE "
                "FILE_FORMAT=(FORMAT_NAME=HLA_CANONICAL_CSV);"
            ),
        ],
        post_load_validation_queries=[
            "SELECT COUNT(*) FROM HEALTHCARE_LANGUAGE_AI.RAW.RAW_CLINICAL_DOCUMENTS;",
            "SELECT COUNT(*) FROM HEALTHCARE_LANGUAGE_AI.RAW.RAW_DOCUMENT_ANNOTATIONS;",
        ],
        required_target_state_role="HLA_INGESTION_ROLE",
        dry_run_status="validated",
        execution_prohibited=True,
        no_connection_attempted=True,
    )


def validate_table_contracts(contracts: list[SnowflakeTableContract]) -> bool:
    return all(
        column.snowflake_type in SUPPORTED_TYPES for table in contracts for column in table.columns
    )
