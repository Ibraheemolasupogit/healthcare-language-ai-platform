"""Document quality checks for preprocessing outputs."""

from __future__ import annotations

from collections import Counter

from healthcare_language_ai.preprocessing.contracts import DocumentQualityMetric


def _metric(
    *,
    document_id: str,
    check_name: str,
    passed: bool,
    observed: str,
    threshold: str,
    message: str,
    run_id: str,
    warning: bool = False,
) -> DocumentQualityMetric:
    status = "passed" if passed else "warning" if warning else "failed"
    return DocumentQualityMetric(
        document_id=document_id,
        check_name=check_name,
        status=status,
        severity="info" if passed else "warning" if warning else "error",
        observed_value=observed,
        threshold=threshold,
        message=message,
        preprocessing_run_id=run_id,
    )


def document_quality_metrics(
    *,
    document_id: str,
    text: str,
    section_count: int,
    sentence_lengths: list[int],
    projection_status_counts: dict[str, int],
    minimum_document_length: int,
    maximum_sentence_length: int,
    run_id: str,
) -> list[DocumentQualityMetric]:
    metrics = [
        _metric(
            document_id=document_id,
            check_name="empty_text",
            passed=bool(text.strip()),
            observed=str(len(text.strip())),
            threshold=">0",
            message="document text is non-empty",
            run_id=run_id,
        ),
        _metric(
            document_id=document_id,
            check_name="very_short_text",
            passed=len(text) >= minimum_document_length,
            observed=str(len(text)),
            threshold=str(minimum_document_length),
            message="document is above minimum configured length",
            run_id=run_id,
            warning=True,
        ),
        _metric(
            document_id=document_id,
            check_name="unicode_replacement_character",
            passed="\ufffd" not in text,
            observed=str(text.count("\ufffd")),
            threshold="0",
            message="no Unicode replacement character detected",
            run_id=run_id,
        ),
        _metric(
            document_id=document_id,
            check_name="section_coverage",
            passed=section_count > 0,
            observed=str(section_count),
            threshold=">0",
            message="at least one section parsed",
            run_id=run_id,
            warning=True,
        ),
    ]
    longest = max(sentence_lengths) if sentence_lengths else 0
    metrics.append(
        _metric(
            document_id=document_id,
            check_name="extremely_long_sentence",
            passed=longest <= maximum_sentence_length,
            observed=str(longest),
            threshold=str(maximum_sentence_length),
            message="sentence length within configured maximum",
            run_id=run_id,
            warning=True,
        )
    )
    unresolved = projection_status_counts.get("unresolved", 0)
    metrics.append(
        _metric(
            document_id=document_id,
            check_name="annotation_projection_success",
            passed=unresolved == 0,
            observed=str(unresolved),
            threshold="0",
            message="all span annotations projected or retained",
            run_id=run_id,
            warning=True,
        )
    )
    return metrics


def quality_status_counts(metrics: list[DocumentQualityMetric]) -> dict[str, int]:
    return dict(sorted(Counter(metric.status for metric in metrics).items()))
