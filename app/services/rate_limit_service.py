from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass
class RateLimitRule:
    limit: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, rule: RateLimitRule) -> bool:
        now = monotonic()
        floor = now - rule.window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < floor:
                bucket.popleft()
            if len(bucket) >= rule.limit:
                return False
            bucket.append(now)
            return True

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()
