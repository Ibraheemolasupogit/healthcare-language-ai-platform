"""Enumerations used by domain models."""

from enum import StrEnum


class ClinicalDocumentType(StrEnum):
    """Supported synthetic clinical document categories."""

    CLINICAL_NOTE = "clinical_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    REFERRAL_LETTER = "referral_letter"
    RADIOLOGY_REPORT = "radiology_report"
    PATHOLOGY_REPORT = "pathology_report"


class ProcessingStatus(StrEnum):
    """Lifecycle states for foundation processing contracts."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


class DataClassification(StrEnum):
    """Allowed non-real-patient data classifications."""

    SYNTHETIC = "synthetic"
    PUBLIC = "public"
    RESTRICTED = "restricted"


class PipelineStage(StrEnum):
    """Target-state pipeline stages without implementing their behavior."""

    INGESTION = "ingestion"
    PREPROCESSING = "preprocessing"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    EMBEDDINGS = "embeddings"
    RETRIEVAL = "retrieval"
    INFERENCE = "inference"
    EVALUATION = "evaluation"
    MONITORING = "monitoring"
    REPORTING = "reporting"
