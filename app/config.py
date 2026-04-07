from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic import model_validator
from typing_extensions import Literal

from app.secrets import SecretResolver


class ProviderConfig(BaseModel):
    enabled: bool = True
    base_url: str
    api_key: str | None = None
    models: dict[str, str] = Field(default_factory=dict)
    generation: dict[str, Any] = Field(default_factory=dict)


class RoutingProfile(BaseModel):
    provider: str
    model: str


class LLMSettings(BaseModel):
    default_provider: str
    default_profile: str
    timeout_seconds: int = 120
    max_retries: int = 2
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    routing: dict[str, dict[str, RoutingProfile]] = Field(default_factory=dict)


class StorageSettings(BaseModel):
    backend: Literal["file", "sqlite", "postgres"] = "file"
    sqlite_path: str | None = None
    postgres_dsn: str | None = None

    @model_validator(mode="after")
    def validate_backend_requirements(self) -> "StorageSettings":
        if self.backend == "postgres" and not self.postgres_dsn:
            raise ValueError("storage.postgres_dsn is required when storage.backend=postgres")
        return self


class SecuritySettings(BaseModel):
    enabled: bool = False
    api_key_header: str = "X-Admin-Key"
    api_key: str | None = None
    principals: list["SecurityPrincipal"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_access_configuration(self) -> "SecuritySettings":
        if not self.enabled:
            return self
        if not self.api_key and not self.principals:
            raise ValueError("security.api_key or security.principals is required when security.enabled=true")
        principal_names = [principal.name for principal in self.principals]
        if len(principal_names) != len(set(principal_names)):
            raise ValueError("security.principals names must be unique")
        if self.principals:
            if any(not principal.api_key for principal in self.principals):
                raise ValueError("security.principals api_key values must not be empty")
            if not any(principal.role == "admin" for principal in self.principals):
                raise ValueError("security.principals must include at least one admin principal")
        return self


class RateLimitSettings(BaseModel):
    enabled: bool = False
    backend: Literal["memory", "redis"] = "memory"
    requests: int = 120
    window_seconds: int = 60
    redis_url: str | None = None
    key_prefix: str = "learn-new:rate"

    @model_validator(mode="after")
    def validate_backend_requirements(self) -> "RateLimitSettings":
        if self.enabled and self.backend == "redis" and not self.redis_url:
            raise ValueError("rate_limit.redis_url is required when rate_limit.backend=redis")
        return self


class ObservabilitySettings(BaseModel):
    metrics_enabled: bool = True
    request_id_header: str = "X-Request-ID"
    trace_id_header: str = "X-Trace-ID"
    audit_log_path: str | None = ".learn/audit/events.jsonl"
    app_log_path: str | None = ".learn/logs/app.jsonl"
    audit_log_max_lines: int | None = 5000
    app_log_max_lines: int | None = 5000


class SandboxSettings(BaseModel):
    backend: Literal["local", "docker"] = "local"
    timeout_seconds: int = 10
    docker_image: str = "python:3.12-slim"
    memory_mb: int = 256
    cpu_limit: float = 1.0

    @model_validator(mode="after")
    def validate_backend_requirements(self) -> "SandboxSettings":
        if self.backend == "docker" and not self.docker_image:
            raise ValueError("sandbox.docker_image is required when sandbox.backend=docker")
        return self


class KnowledgeSettings(BaseModel):
    backend: Literal["file", "qdrant"] = "file"
    qdrant_url: str | None = None
    collection_name: str = "learn-new"
    vector_size: int = 16

    @model_validator(mode="after")
    def validate_backend_requirements(self) -> "KnowledgeSettings":
        if self.backend == "qdrant" and not self.qdrant_url:
            raise ValueError("knowledge.qdrant_url is required when knowledge.backend=qdrant")
        return self


class SecurityPrincipal(BaseModel):
    name: str
    api_key: str
    role: Literal["viewer", "operator", "admin"] = "viewer"


class AppConfig(BaseModel):
    version: int = 1
    llm: LLMSettings
    storage: StorageSettings = Field(default_factory=StorageSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    knowledge: KnowledgeSettings = Field(default_factory=KnowledgeSettings)
    tasks: "TaskQueueSettings" = Field(default_factory=lambda: TaskQueueSettings())

    @model_validator(mode="after")
    def validate_cross_field_settings(self) -> "AppConfig":
        if self.tasks.backend == "postgres":
            if not self.tasks.postgres_dsn and self.storage.backend == "postgres":
                self.tasks.postgres_dsn = self.storage.postgres_dsn
            if not self.tasks.postgres_dsn:
                raise ValueError("tasks.postgres_dsn is required when tasks.backend=postgres")
        return self


class TaskQueueSettings(BaseModel):
    enabled: bool = True
    backend: Literal["memory", "sqlite", "postgres"] = "memory"
    worker_threads: int = 1
    max_queue_size: int = 100
    max_attempts: int = 1
    sqlite_path: str | None = None
    postgres_dsn: str | None = None

    @model_validator(mode="after")
    def validate_queue_settings(self) -> "TaskQueueSettings":
        if self.worker_threads < 1:
            raise ValueError("tasks.worker_threads must be at least 1")
        if self.max_queue_size < 1:
            raise ValueError("tasks.max_queue_size must be at least 1")
        if self.max_attempts < 1:
            raise ValueError("tasks.max_attempts must be at least 1")
        if self.backend == "sqlite" and not self.sqlite_path:
            self.sqlite_path = ".learn/tasks.db"
        return self


def load_config(path: Path | str = "config/llm.yaml") -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return AppConfig.model_validate(_resolve_env_refs(raw, resolver=SecretResolver()))


def _resolve_env_refs(value: Any, resolver: SecretResolver) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_env_refs(inner, resolver=resolver) for key, inner in value.items()}
    if isinstance(value, list):
        return [_resolve_env_refs(item, resolver=resolver) for item in value]
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return resolver.resolve(value)
    return value
