# Local API

The FastAPI service is local, read-only, synthetic-only, and non-clinical.

Endpoints include:

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/system`
- `GET /api/v1/approvals/retrieval`
- `GET /api/v1/approvals/rag`
- `GET /api/v1/quality-gates/retrieval`
- `GET /api/v1/quality-gates/rag`
- `POST /api/v1/query`
- `GET /api/v1/answers/{answer_id}`
- `GET /api/v1/traces/{answer_id}`
- `GET /api/v1/evidence/{evidence_id}`
- `GET /api/v1/citations/{citation_id}`
- `GET /api/v1/metrics/summary`

Default host is `127.0.0.1`. CORS is disabled by default. Security headers include `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control`, and a restrictive content security policy. Responses do not expose stack traces, credentials, absolute paths, full source documents, or full event payload text.

Run locally:

```bash
python3 -m healthcare_language_ai api-run --host 127.0.0.1 --port 8000
```
