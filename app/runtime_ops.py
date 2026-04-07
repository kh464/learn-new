from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import time


class InMemoryRateLimiter:
    def __init__(self, requests: int, window_seconds: int) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time()
        with self._lock:
            events = self._events[key]
            while events and now - events[0] >= self.window_seconds:
                events.popleft()
            if len(events) >= self.requests:
                return False
            events.append(now)
            return True


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self.request_count = 0
        self.latency_ms_total = 0.0
        self.status_counts: dict[int, int] = defaultdict(int)

    def record(self, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self.request_count += 1
            self.latency_ms_total += latency_ms
            self.status_counts[status_code] += 1

    def render_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP learn_new_requests_total Total HTTP requests served.",
                "# TYPE learn_new_requests_total counter",
                f"learn_new_requests_total {self.request_count}",
                "# HELP learn_new_request_latency_ms_total Aggregate HTTP latency in milliseconds.",
                "# TYPE learn_new_request_latency_ms_total counter",
                f"learn_new_request_latency_ms_total {self.latency_ms_total:.3f}",
                "# HELP learn_new_requests_by_status_total HTTP requests partitioned by status code.",
                "# TYPE learn_new_requests_by_status_total counter",
            ]
            for status_code, count in sorted(self.status_counts.items()):
                lines.append(f'learn_new_requests_by_status_total{{status="{status_code}"}} {count}')
        return "\n".join(lines) + "\n"
