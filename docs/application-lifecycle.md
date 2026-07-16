# Application Lifecycle

The FastAPI app now uses a lifespan hook to build local services and verify
readiness at startup. Startup failure is explicit when required local
components are not ready.

This is a local lifecycle guard only. It does not add production orchestration,
external service discovery, or cloud health management.
