from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from typing_extensions import Literal


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


class SecuritySettings(BaseModel):
    enabled: bool = False
    api_key_header: str = "X-Admin-Key"
    api_key: str | None = None
    principals: list["SecurityPrincipal"] = Field(default_factory=list)


class RateLimitSettings(BaseModel):
    enabled: bool = False
    backend: Literal["memory", "redis"] = "memory"
    requests: int = 120
    window_seconds: int = 60
    redis_url: str | None = None
    key_prefix: str = "learn-new:rate"


class ObservabilitySettings(BaseModel):
    metrics_enabled: bool = True
    request_id_header: str = "X-Request-ID"
    audit_log_path: str | None = ".learn/audit/events.jsonl"


class SandboxSettings(BaseModel):
    backend: Literal["local", "docker"] = "local"
    timeout_seconds: int = 10
    docker_image: str = "python:3.12-slim"
    memory_mb: int = 256
    cpu_limit: float = 1.0


class KnowledgeSettings(BaseModel):
    backend: Literal["file", "qdrant"] = "file"
    qdrant_url: str | None = None
    collection_name: str = "learn-new"
    vector_size: int = 16


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


def load_config(path: Path | str = "config/llm.yaml") -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return AppConfig.model_validate(_resolve_env_refs(raw))


def _resolve_env_refs(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_env_refs(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_resolve_env_refs(item) for item in value]
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1])
    return value
