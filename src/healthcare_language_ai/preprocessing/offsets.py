"""Annotation projection with no-guess offset policy."""

from __future__ import annotations

from healthcare_language_ai.ingestion.contracts import CanonicalDocumentAnnotation
from healthcare_language_ai.preprocessing.contracts import ProjectedAnnotation
from healthcare_language_ai.utils.identifiers import deterministic_id


def project_annotations(
    *,
    annotations: list[CanonicalDocumentAnnotation],
    source_text_by_document: dict[str, str],
    normalised_text_by_document: dict[str, str],
    run_id: str,
) -> list[ProjectedAnnotation]:
    rows: list[ProjectedAnnotation] = []
    for annotation in annotations:
        status = "not_applicable"
        target_start: int | None = None
        target_end: int | None = None
        rule = "document_level_no_offsets"
        if annotation.annotation_type == "span":
            source = source_text_by_document[annotation.document_id]
            target = normalised_text_by_document[annotation.document_id]
            if (
                source == target
                and annotation.start_offset is not None
                and annotation.end_offset is not None
                and source[annotation.start_offset : annotation.end_offset] == annotation.value
            ):
                status = "unchanged"
                target_start = annotation.start_offset
                target_end = annotation.end_offset
                rule = "source_text_unchanged"
            else:
                positions = [
                    index
                    for index in range(len(target))
                    if target.startswith(annotation.value, index)
                ]
                if len(positions) == 1:
                    status = "projected"
                    target_start = positions[0]
                    target_end = positions[0] + len(annotation.value)
                    rule = "unique_value_match"
                else:
                    status = "unresolved"
                    rule = "ambiguous_or_missing_value"
        rows.append(
            ProjectedAnnotation(
                projection_id=deterministic_id(
                    [run_id, annotation.annotation_id, status], prefix="PROJ", length=24
                ),
                annotation_id=annotation.annotation_id,
                document_id=annotation.document_id,
                annotation_type=annotation.annotation_type,
                label=annotation.label,
                value=annotation.value,
                source_start=annotation.start_offset,
                source_end=annotation.end_offset,
                target_start=target_start,
                target_end=target_end,
                projection_status=status,
                projection_rule=rule,
                preprocessing_run_id=run_id,
            )
        )
    return rows
