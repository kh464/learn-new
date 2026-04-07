from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib import error, request

from app.config import AppConfig


class RuntimeHealthService:
    def __init__(self, config: AppConfig, workspace_root: Path | str) -> None:
        self.config = config
        self.workspace_root = Path(workspace_root)

    def readiness_payload(self) -> dict:
        checks = self.checks()
        healthy = all(item["healthy"] for item in checks.values())
        return {
            "status": "ok" if healthy else "degraded",
            "storage_backend": self.config.storage.backend,
            "knowledge_backend": self.config.knowledge.backend,
            "sandbox_backend": self.config.sandbox.backend,
            "metrics_enabled": self.config.observability.metrics_enabled,
            "security_enabled": self.config.security.enabled,
            "rate_limit_enabled": self.config.rate_limit.enabled,
            "rate_limit_backend": self.config.rate_limit.backend,
            "checks": checks,
        }

    def runtime_summary(
        self,
        metrics_snapshot: dict,
        audit_enabled: bool,
        audit_recent_count: int,
        app_log_enabled: bool,
        app_log_recent_count: int,
        task_queue_enabled: bool,
        task_queue_snapshot: dict | None,
        session_total: int,
    ) -> dict:
        checks = self.checks()
        return {
            "healthy": all(item["healthy"] for item in checks.values()),
            "backends": {
                "storage": self.config.storage.backend,
                "knowledge": self.config.knowledge.backend,
                "sandbox": self.config.sandbox.backend,
                "rate_limit": self.config.rate_limit.backend if self.config.rate_limit.enabled else "disabled",
                "security": "enabled" if self.config.security.enabled else "disabled",
            },
            "checks": checks,
            "metrics": metrics_snapshot,
            "audit": {
                "enabled": audit_enabled,
                "recent_count": audit_recent_count,
            },
            "app_logs": {
                "enabled": app_log_enabled,
                "recent_count": app_log_recent_count,
                "path": self.config.observability.app_log_path,
            },
            "tasks": {
                "enabled": task_queue_enabled,
                "snapshot": task_queue_snapshot,
            },
            "sessions": {
                "total": session_total,
            },
            "security": _probe_security(self.config),
        }

    def checks(self) -> dict[str, dict]:
        return {
            "storage": _safe_probe(lambda: _probe_storage(self.config, self.workspace_root), self.config.storage.backend),
            "knowledge": _safe_probe(lambda: _probe_knowledge(self.config), self.config.knowledge.backend),
            "sandbox": _safe_probe(lambda: _probe_sandbox(self.config), self.config.sandbox.backend),
            "rate_limit": _safe_probe(
                lambda: _probe_rate_limit(self.config),
                self.config.rate_limit.backend if self.config.rate_limit.enabled else "disabled",
            ),
            "security": _safe_probe(
                lambda: _probe_security(self.config),
                "principals" if self.config.security.principals else ("shared_key" if self.config.security.enabled else "disabled"),
            ),
        }


def _safe_probe(factory, backend: str) -> dict:
    try:
        return factory()
    except Exception as exc:
        return {
            "healthy": False,
            "backend": backend,
            "detail": str(exc),
        }


def _probe_storage(config: AppConfig, workspace_root: Path) -> dict:
    if config.storage.backend == "file":
        return {
            "healthy": True,
            "backend": "file",
            "detail": f"Workspace root: {workspace_root.as_posix()}",
        }
    if config.storage.backend == "sqlite":
        sqlite_path = Path(config.storage.sqlite_path) if config.storage.sqlite_path else workspace_root / "sessions.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(sqlite_path) as connection:
            connection.execute("SELECT 1")
        return {
            "healthy": True,
            "backend": "sqlite",
            "detail": f"SQLite reachable at {sqlite_path.as_posix()}",
        }
    _probe_postgres(config.storage.postgres_dsn or "")
    return {
        "healthy": True,
        "backend": "postgres",
        "detail": "PostgreSQL ping succeeded.",
    }


def _probe_rate_limit(config: AppConfig) -> dict:
    if not config.rate_limit.enabled:
        return {
            "healthy": True,
            "backend": "disabled",
            "detail": "Rate limiting is disabled.",
        }
    if config.rate_limit.backend == "memory":
        return {
            "healthy": True,
            "backend": "memory",
            "detail": "In-memory limiter active.",
        }
    _probe_redis(config.rate_limit.redis_url or "")
    return {
        "healthy": True,
        "backend": "redis",
        "detail": "Redis ping succeeded.",
    }


def _probe_knowledge(config: AppConfig) -> dict:
    if config.knowledge.backend == "file":
        return {
            "healthy": True,
            "backend": "file",
            "detail": "File-backed knowledge index active.",
        }
    _probe_qdrant(config.knowledge.qdrant_url or "")
    return {
        "healthy": True,
        "backend": "qdrant",
        "detail": "Qdrant HTTP probe succeeded.",
    }


def _probe_sandbox(config: AppConfig) -> dict:
    if config.sandbox.backend == "local":
        return {
            "healthy": True,
            "backend": "local",
            "detail": f"Python interpreter: {sys.executable}",
        }
    _probe_docker()
    return {
        "healthy": True,
        "backend": "docker",
        "detail": "Docker daemon probe succeeded.",
    }


def _probe_security(config: AppConfig) -> dict:
    if not config.security.enabled:
        return {
            "healthy": True,
            "backend": "disabled",
            "detail": "Security middleware is disabled.",
            "principal_count": 0,
            "roles": [],
        }
    if config.security.principals:
        return {
            "healthy": True,
            "backend": "principals",
            "detail": f"{len(config.security.principals)} principals configured.",
            "principal_count": len(config.security.principals),
            "roles": sorted({principal.role for principal in config.security.principals}),
        }
    return {
        "healthy": True,
        "backend": "shared_key",
        "detail": "Shared admin key configured.",
        "principal_count": 1,
        "roles": ["admin"],
    }


def _probe_postgres(dsn: str) -> None:
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=3) as connection:
            connection.execute("SELECT 1")
    except ImportError:
        import psycopg2

        connection = psycopg2.connect(dsn, connect_timeout=3)
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        finally:
            connection.close()


def _probe_redis(redis_url: str) -> None:
    import redis

    client = redis.Redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
    client.ping()


def _probe_qdrant(base_url: str) -> None:
    req = request.Request(f"{base_url.rstrip('/')}/collections", method="GET")
    try:
        with request.urlopen(req, timeout=3) as response:
            if response.status >= 400:
                raise RuntimeError(f"Qdrant probe failed with status {response.status}")
    except error.URLError as exc:
        raise RuntimeError("Qdrant probe failed") from exc


def _probe_docker() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker executable not found")
    completed = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "docker version returned a non-zero exit code"
        raise RuntimeError(stderr)
