"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError

from healthcare_language_ai.api.dependencies import get_services
from healthcare_language_ai.api.errors import ApiErrorResponseError
from healthcare_language_ai.api.lifespan import lifespan
from healthcare_language_ai.api.middleware import request_context_middleware
from healthcare_language_ai.api.rate_limit import LocalRateLimiter
from healthcare_language_ai.application.contracts import (
    AnswerResponse,
    ApiError,
    ApprovalResponse,
    CitationResponse,
    EvidenceResponse,
    HealthResponse,
    MetricSummaryResponse,
    QualityGateResponse,
    QueryRequest,
    QueryResponse,
    ReadinessResponse,
    SystemStatusResponse,
    TraceResponse,
)

DESCRIPTION = (
    "Synthetic-only local portfolio demonstration API. Not for patient care, not medical "
    "advice, not clinically validated, and not connected to real patient systems."
)


def create_app() -> FastAPI:
    services = get_services()
    app = FastAPI(
        title="Healthcare Language AI Local Demonstration API",
        version="v1",
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.middleware("http")(request_context_middleware)
    limiter = LocalRateLimiter(
        requests=services.settings.milestone11.rate_limit_requests,
        window_seconds=services.settings.milestone11.rate_limit_window_seconds,
        enabled=services.settings.milestone11.rate_limit_enabled,
    )

    @app.exception_handler(ApiErrorResponseError)
    async def api_error_handler(request: Request, exc: ApiErrorResponseError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiError(
                error_code=exc.error_code,
                message=exc.message,
                request_id=request_id,
                status=exc.status_code,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=422,
            content=ApiError(
                error_code="schema_validation_failed",
                message="Request or response schema validation failed.",
                request_id=request_id,
                status=422,
                details={"error_count": str(len(exc.errors()))},
            ).model_dump(mode="json"),
        )

    @app.get("/health/live", tags=["health"])
    def live() -> HealthResponse:
        return get_services().health.live()

    @app.get("/health/ready", tags=["health"])
    def ready() -> ReadinessResponse:
        readiness = get_services().health.ready()
        if readiness.status != "ready":
            raise ApiErrorResponseError("system_not_ready", "Readiness checks failed.", 503)
        return readiness

    @app.get("/api/v1/system", tags=["system"])
    def system() -> SystemStatusResponse:
        return get_services().health.system_status()

    @app.get("/api/v1/approvals/retrieval", tags=["approvals"])
    def retrieval_approval() -> ApprovalResponse:
        return get_services().approval.retrieval_approval()

    @app.get("/api/v1/approvals/rag", tags=["approvals"])
    def rag_approval() -> ApprovalResponse:
        return get_services().approval.rag_approval()

    @app.get("/api/v1/quality-gates/retrieval", tags=["quality"])
    def retrieval_gates() -> QualityGateResponse:
        return get_services().approval.retrieval_gates()

    @app.get("/api/v1/quality-gates/rag", tags=["quality"])
    def rag_gates() -> QualityGateResponse:
        return get_services().approval.rag_gates()

    @app.post("/api/v1/query", tags=["query"])
    def query(request: QueryRequest, http_request: Request) -> QueryResponse:
        client = http_request.client.host if http_request.client else "local"
        if not limiter.allow(client):
            raise ApiErrorResponseError("rate_limit_exceeded", "Local rate limit exceeded.", 429)
        try:
            return get_services().query.run_synthetic_query(request)
        except PermissionError as exc:
            raise ApiErrorResponseError("portfolio_demo_mode_required", str(exc), 403) from exc
        except ValueError as exc:
            raise ApiErrorResponseError(
                str(exc), "Query request is outside local demo limits.", 400
            ) from exc

    @app.get("/api/v1/answers/{answer_id}", tags=["answers"])
    def answer(answer_id: str, request: Request) -> AnswerResponse:
        try:
            return get_services().evidence.answer_response(answer_id, request.state.request_id)
        except KeyError as exc:
            raise ApiErrorResponseError(
                "answer_not_found", "Answer ID was not found.", 404
            ) from exc

    @app.get("/api/v1/traces/{answer_id}", tags=["traces"])
    def trace(answer_id: str) -> TraceResponse:
        try:
            return get_services().trace.get_trace(answer_id)
        except KeyError as exc:
            raise ApiErrorResponseError(
                "trace_not_found", "Trace target was not found.", 404
            ) from exc

    @app.get("/api/v1/evidence/{evidence_id}", tags=["evidence"])
    def evidence(evidence_id: str) -> EvidenceResponse:
        try:
            return get_services().evidence.evidence_response(evidence_id)
        except KeyError as exc:
            raise ApiErrorResponseError(
                "evidence_not_found", "Evidence ID was not found.", 404
            ) from exc

    @app.get("/api/v1/citations/{citation_id}", tags=["citations"])
    def citation(citation_id: str) -> CitationResponse:
        try:
            return get_services().evidence.citation_response(citation_id)
        except KeyError as exc:
            raise ApiErrorResponseError(
                "citation_not_found", "Citation ID was not found.", 404
            ) from exc

    @app.get("/api/v1/metrics/summary", tags=["metrics"])
    def metric_summary() -> MetricSummaryResponse:
        return get_services().metrics.summary()

    @app.get("/api/v1/metrics/retrieval", tags=["metrics"])
    def retrieval_metrics() -> MetricSummaryResponse:
        return get_services().metrics.summary()

    @app.get("/api/v1/metrics/rag", tags=["metrics"])
    def rag_metrics() -> MetricSummaryResponse:
        return get_services().metrics.summary()

    @app.get("/metrics", include_in_schema=False)
    def prometheus() -> PlainTextResponse:
        services = get_services()
        return PlainTextResponse(services.metrics.prometheus(services.health.ready().status))

    return app


app = create_app()
