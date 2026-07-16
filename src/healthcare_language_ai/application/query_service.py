"""Synthetic query execution through the approved read-only RAG fixture layer."""

from __future__ import annotations

import time
import uuid

from healthcare_language_ai.application.contracts import DISCLAIMER, QueryRequest, QueryResponse
from healthcare_language_ai.application.evidence_service import EvidenceService
from healthcare_language_ai.application.metrics_service import MetricsService
from healthcare_language_ai.application.trace_service import TraceService
from healthcare_language_ai.config import AppSettings
from healthcare_language_ai.observability.events import make_event
from healthcare_language_ai.rag.contracts import RagAnswer
from healthcare_language_ai.rag.query_safety import classify_query


class QueryService:
    def __init__(
        self,
        settings: AppSettings,
        evidence: EvidenceService,
        trace: TraceService,
        metrics: MetricsService,
    ) -> None:
        self.settings = settings
        self.evidence = evidence
        self.trace = trace
        self.metrics = metrics

    def run_synthetic_query(self, request: QueryRequest) -> QueryResponse:
        started = time.perf_counter()
        request_id = f"REQ-{uuid.uuid4().hex[:24]}"
        if len(request.query_text) > self.settings.milestone10.maximum_query_characters:
            self.metrics.record(
                make_event(
                    event_type="application_error",
                    request_id=request_id,
                    query_text=request.query_text,
                    error_code="query_too_large",
                )
            )
            raise ValueError("query_too_large")
        if len(request.metadata_filters) > self.settings.milestone10.maximum_metadata_filters:
            raise ValueError("too_many_metadata_filters")
        if not request.portfolio_demo_mode:
            raise PermissionError("portfolio_demo_mode_required")
        query_id = request.query_id or self._match_query_text(request.query_text)
        classification = classify_query(
            query_id=query_id or "ad-hoc", query_text=request.query_text
        )
        if not classification.allowed_for_retrieval:
            response = QueryResponse(
                request_id=request_id,
                query_id=query_id or classification.query_id,
                answer_id=f"REF-{uuid.uuid5(uuid.NAMESPACE_URL, request_id).hex[:24]}",
                answer_status="unsupported_request_refusal",
                answer_text=(
                    "This local synthetic portfolio demonstration cannot provide clinical, "
                    "real-patient, medication, treatment, diagnosis, or emergency guidance. "
                    + DISCLAIMER
                ),
                citations=[],
                retrieval_status="not_invoked",
                retrieval_confidence=0.0,
                trace_id=request_id,
            )
            self.metrics.record(
                make_event(
                    event_type="query_refused_before_retrieval",
                    request_id=request_id,
                    query_text=request.query_text,
                    query_category=classification.category,
                    answer_status=response.answer_status,
                    safety_status="passed",
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            )
            return response
        if query_id is None or query_id not in self.evidence.answer_by_query_id:
            answer = self._first_answer_by_status("unanswerable_refusal")
        else:
            answer = self.evidence.answer_by_query_id[query_id]
        response = self.evidence.query_response(answer, request_id)
        event_type = (
            "retrieval_abstained"
            if response.retrieval_status == "retrieval_abstained"
            else "answer_generated"
        )
        self.metrics.record(
            make_event(
                event_type="query_accepted",
                request_id=request_id,
                query_text=request.query_text,
                query_category=classification.category,
                retrieval_status=response.retrieval_status,
                answer_status=response.answer_status,
                citation_status="passed" if response.citations else "",
                groundedness_status="passed",
                safety_status="passed",
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        )
        self.metrics.record(
            make_event(
                event_type=event_type,
                request_id=request_id,
                query_text=request.query_text,
                query_category=classification.category,
                retrieval_status=response.retrieval_status,
                answer_status=response.answer_status,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        )
        return response

    def _match_query_text(self, query_text: str) -> str | None:
        normalised = " ".join(query_text.lower().split())
        for query in self.evidence.queries:
            if " ".join(str(query["query_text"]).lower().split()) == normalised:
                return str(query["query_id"])
        return None

    def _first_answer_by_status(self, status: str) -> RagAnswer:
        for answer in self.evidence.answers:
            if answer.answer_status == status:
                return answer
        for answer in self.evidence.answers:
            if "refusal" in answer.answer_status:
                return answer
        return self.evidence.answers[0]
