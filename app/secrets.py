from __future__ import annotations

import os
from pathlib import Path


class SecretResolver:
    def __init__(self, secret_dir: Path | str | None = None) -> None:
        configured = secret_dir or os.getenv("LEARN_NEW_SECRET_DIR")
        self.secret_dir = Path(configured) if configured else None

    def resolve(self, expression: str) -> str | None:
        if expression.startswith("${") and expression.endswith("}"):
            token = expression[2:-1]
        else:
            token = expression

        if token.startswith("secret:"):
            return self._from_secret_dir(token.split(":", 1)[1])
        if token.startswith("file:"):
            return self._from_file(token.split(":", 1)[1])
        return os.getenv(token)

    def _from_secret_dir(self, name: str) -> str | None:
        if self.secret_dir is None:
            return None
        path = self.secret_dir / name
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip()

    def _from_file(self, raw_path: str) -> str | None:
        path = Path(raw_path)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip()
