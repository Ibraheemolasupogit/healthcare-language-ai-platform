# API Contracts

API contracts are Pydantic models exported through `healthcare_language_ai.api.schemas` and JSON Schema files under `schemas/`.

Checked-in fixtures under `tests/fixtures/api/` include OpenAPI, route inventory, example query request, grounded response, refusal response, trace response, and readiness response. These fixtures are deterministic after runtime request IDs and timestamps are normalized.
