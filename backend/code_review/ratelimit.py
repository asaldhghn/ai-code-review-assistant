"""A tiny in-memory sliding-window rate limiter (per client key), for live AI reviews.

It protects a shared deployment from request floods. It is per-process, which is enough for a
single instance; a multi-instance deployment would use a shared store such as Redis.
"""

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0, clock=time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        # Drop idle keys so memory does not grow without bound.
        if len(self._hits) > 10_000:
            for stale in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
                self._hits.pop(stale, None)
        return True
