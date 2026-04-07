from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import request


class SecretResolver:
    def __init__(
        self,
        secret_dir: Path | str | None = None,
        vault_addr: str | None = None,
        vault_token: str | None = None,
        vault_token_file: Path | str | None = None,
        vault_namespace: str | None = None,
    ) -> None:
        configured = secret_dir or os.getenv("LEARN_NEW_SECRET_DIR")
        self.secret_dir = Path(configured) if configured else None
        self.vault_addr = (vault_addr or os.getenv("LEARN_NEW_VAULT_ADDR") or "").strip()
        self.vault_namespace = (vault_namespace or os.getenv("LEARN_NEW_VAULT_NAMESPACE") or "").strip() or None
        token_file = vault_token_file or os.getenv("LEARN_NEW_VAULT_TOKEN_FILE")
        self.vault_token = (vault_token or os.getenv("LEARN_NEW_VAULT_TOKEN") or "").strip()
        if not self.vault_token and token_file:
            self.vault_token = self._read_text(Path(token_file))
        self._vault_cache: dict[str, dict[str, object]] = {}

    def resolve(self, expression: str) -> str | None:
        if expression.startswith("${") and expression.endswith("}"):
            token = expression[2:-1]
        else:
            token = expression

        if token.startswith("secret:"):
            return self._from_secret_dir(token.split(":", 1)[1])
        if token.startswith("file:"):
            return self._from_file(token.split(":", 1)[1])
        if token.startswith("vault:"):
            return self._from_vault(token.split(":", 1)[1])
        return os.getenv(token)

    def _from_secret_dir(self, name: str) -> str | None:
        if self.secret_dir is None:
            return None
        path = self.secret_dir / name
        if not path.exists():
            return None
        return self._read_text(path)

    def _from_file(self, raw_path: str) -> str | None:
        path = Path(raw_path)
        if not path.exists():
            return None
        return self._read_text(path)

    def _from_vault(self, secret_spec: str) -> str | None:
        if not self.vault_addr:
            raise RuntimeError("LEARN_NEW_VAULT_ADDR is required for vault: references")
        if not self.vault_token:
            raise RuntimeError("LEARN_NEW_VAULT_TOKEN or LEARN_NEW_VAULT_TOKEN_FILE is required for vault: references")

        path, _, field = secret_spec.partition("#")
        field_name = field or "value"
        payload = self._load_vault_secret(path)
        value = payload.get(field_name)
        if value is None:
            return None
        return str(value)

    def _load_vault_secret(self, path: str) -> dict[str, object]:
        normalized_path = path.strip("/")
        if normalized_path in self._vault_cache:
            return self._vault_cache[normalized_path]

        headers = {"X-Vault-Token": self.vault_token}
        if self.vault_namespace:
            headers["X-Vault-Namespace"] = self.vault_namespace

        req = request.Request(f"{self.vault_addr.rstrip('/')}/v1/{normalized_path}", headers=headers, method="GET")
        with request.urlopen(req, timeout=5) as response:
            raw_payload = json.loads(response.read().decode("utf-8"))
        data = raw_payload.get("data", {})
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data["data"]
        if not isinstance(data, dict):
            raise RuntimeError(f"Vault response for {normalized_path} did not contain a secret payload")
        self._vault_cache[normalized_path] = data
        return data

    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()
