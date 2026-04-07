from __future__ import annotations

from collections import defaultdict, deque
import json
from threading import Lock
from time import time
from pathlib import Path


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


class RedisRateLimiter:
    def __init__(self, requests: int, window_seconds: int, client, key_prefix: str = "learn-new:rate") -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self.client = client
        self.key_prefix = key_prefix

    def allow(self, key: str) -> bool:
        bucket = f"{self.key_prefix}:{key}"
        count = int(self.client.incr(bucket))
        if count == 1:
            self.client.expire(bucket, self.window_seconds)
        return count <= self.requests


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self.request_count = 0
        self.latency_ms_total = 0.0
        self.status_counts: dict[int, int] = defaultdict(int)
        self.path_status_counts: dict[tuple[str, int], int] = defaultdict(int)

    def record(self, status_code: int, latency_ms: float, path: str = "") -> None:
        with self._lock:
            self.request_count += 1
            self.latency_ms_total += latency_ms
            self.status_counts[status_code] += 1
            if path:
                self.path_status_counts[(path, status_code)] += 1

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
            lines.extend(
                [
                    "# HELP learn_new_requests_by_path_total HTTP requests partitioned by route path and status code.",
                    "# TYPE learn_new_requests_by_path_total counter",
                ]
            )
            for (path, status_code), count in sorted(self.path_status_counts.items()):
                lines.append(
                    f'learn_new_requests_by_path_total{{path="{path}",status="{status_code}"}} {count}'
                )
        return "\n".join(lines) + "\n"

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "request_count": self.request_count,
                "latency_ms_total": round(self.latency_ms_total, 3),
                "status_counts": {str(key): value for key, value in self.status_counts.items()},
                "path_status_counts": {
                    f"{path}|{status_code}": count
                    for (path, status_code), count in self.path_status_counts.items()
                },
            }


class AuditLogger:
    def __init__(self, path: Path, max_lines: int | None = None) -> None:
        self.path = Path(path)
        self.max_lines = max_lines
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append(self, payload: dict) -> None:
        line = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            self._trim_if_needed()

    def read_recent(self, limit: int = 100) -> list[dict]:
        if not self.path.exists():
            return []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        items = [json.loads(line) for line in lines if line.strip()]
        return items[-limit:][::-1]

    def _trim_if_needed(self) -> None:
        if self.max_lines is None or self.max_lines <= 0 or not self.path.exists():
            return
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.max_lines:
            return
        trimmed = lines[-self.max_lines :]
        self.path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")


class AppEventLogger(AuditLogger):
    pass
