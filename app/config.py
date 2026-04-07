from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


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


class AppConfig(BaseModel):
    version: int = 1
    llm: LLMSettings


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
