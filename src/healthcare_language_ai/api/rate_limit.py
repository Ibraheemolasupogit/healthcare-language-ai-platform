"""In-memory local rate limiting for portfolio smoke and API use."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class LocalRateLimiter:
    def __init__(self, requests: int, window_seconds: int, enabled: bool = True) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        if not self.enabled:
            return True
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.requests:
                return False
            hits.append(now)
            return True
