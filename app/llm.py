from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import AppConfig, ProviderConfig, RoutingProfile


class LLMGateway:
    def __init__(
        self,
        config: AppConfig,
        client_factory: type[OpenAI] = OpenAI,
    ) -> None:
        self.config = config
        self.client_factory = client_factory

    def is_available(self, profile: str = "chat") -> bool:
        provider, _route = self._resolve_route(profile)
        return provider.enabled and bool(provider.api_key)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        profile: str = "chat",
    ) -> dict[str, Any]:
        provider, route = self._resolve_route(profile)
        if not provider.enabled or not provider.api_key:
            raise RuntimeError(f"Provider for profile '{profile}' is unavailable.")

        client = self.client_factory(
            api_key=provider.api_key,
            base_url=provider.base_url,
            timeout=self.config.llm.timeout_seconds,
            max_retries=self.config.llm.max_retries,
        )
        response = client.chat.completions.create(
            model=route.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=provider.generation.get("temperature", 0.2),
            top_p=provider.generation.get("top_p", 0.95),
            max_tokens=provider.generation.get("max_tokens", 2048),
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _resolve_route(self, profile: str) -> tuple[ProviderConfig, RoutingProfile]:
        routes = self.config.llm.routing.get("profiles", {})
        route = RoutingProfile.model_validate(routes[profile])
        provider = self.config.llm.providers[route.provider]
        return provider, route
