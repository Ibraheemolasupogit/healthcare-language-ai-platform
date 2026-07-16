"""FastAPI dependency helpers."""

from healthcare_language_ai.application import ApplicationServices, build_services

_SERVICES: ApplicationServices | None = None


def get_services() -> ApplicationServices:
    global _SERVICES
    if _SERVICES is None:
        _SERVICES = build_services()
    return _SERVICES
