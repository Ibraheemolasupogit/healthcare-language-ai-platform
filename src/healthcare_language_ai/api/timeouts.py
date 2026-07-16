"""Cooperative timeout helper."""

from __future__ import annotations

import time
from collections.abc import Callable


def run_with_timeout[T](action: Callable[[], T], timeout_seconds: float) -> T:
    started = time.monotonic()
    result = action()
    if time.monotonic() - started > timeout_seconds:
        msg = "operation_timeout"
        raise TimeoutError(msg)
    return result
