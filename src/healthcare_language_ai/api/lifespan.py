"""FastAPI lifespan validation hooks."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from healthcare_language_ai.application.dependencies import build_services


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    services = build_services()
    readiness = services.health.ready()
    if readiness.status != "ready":
        msg = "startup readiness validation failed"
        raise RuntimeError(msg)
    app.state.services = services
    yield
