from pathlib import Path

from app.config import load_config
from app.secrets import SecretResolver


class _FakeVaultResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> "_FakeVaultResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_load_config_resolves_secret_file_references_from_secret_dir(tmp_path: Path, monkeypatch) -> None:
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    (secret_dir / "siliconflow_api_key").write_text("secret-from-file", encoding="utf-8")
    monkeypatch.setenv("LEARN_NEW_SECRET_DIR", str(secret_dir))

    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: 1",
                "llm:",
                "  default_provider: siliconflow",
                "  default_profile: chat",
                "  providers:",
                "    siliconflow:",
                "      enabled: true",
                "      base_url: https://api.siliconflow.cn/v1",
                "      api_key: ${secret:siliconflow_api_key}",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.llm.providers["siliconflow"].api_key == "secret-from-file"


def test_load_config_resolves_vault_secret_references_with_single_fetch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LEARN_NEW_VAULT_ADDR", "https://vault.internal")
    monkeypatch.setenv("LEARN_NEW_VAULT_TOKEN", "vault-token")
    monkeypatch.setenv("LEARN_NEW_VAULT_NAMESPACE", "platform/team-a")

    requests: list[tuple[str, str | None, str | None]] = []

    def fake_urlopen(req, timeout: int = 0):
        requests.append(
            (
                req.full_url,
                req.get_header("X-vault-token"),
                req.get_header("X-vault-namespace"),
            )
        )
        return _FakeVaultResponse(
            '{"data":{"data":{"siliconflow_api_key":"vault-sf-key","admin_key":"vault-admin-key"}}}'
        )

    monkeypatch.setattr("app.secrets.request.urlopen", fake_urlopen)

    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: 1",
                "llm:",
                "  default_provider: siliconflow",
                "  default_profile: chat",
                "  providers:",
                "    siliconflow:",
                "      enabled: true",
                "      base_url: https://api.siliconflow.cn/v1",
                "      api_key: ${vault:secret/data/learn-new#siliconflow_api_key}",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
                "security:",
                "  enabled: true",
                "  api_key_header: X-Admin-Key",
                "  api_key: ${vault:secret/data/learn-new#admin_key}",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.llm.providers["siliconflow"].api_key == "vault-sf-key"
    assert config.security.api_key == "vault-admin-key"
    assert requests == [("https://vault.internal/v1/secret/data/learn-new", "vault-token", "platform/team-a")]


def test_secret_resolver_reads_vault_token_from_file_and_caches_values(tmp_path: Path, monkeypatch) -> None:
    token_file = tmp_path / "vault.token"
    token_file.write_text("token-from-file", encoding="utf-8")

    monkeypatch.setenv("LEARN_NEW_VAULT_ADDR", "https://vault.internal")
    monkeypatch.delenv("LEARN_NEW_VAULT_TOKEN", raising=False)
    monkeypatch.setenv("LEARN_NEW_VAULT_TOKEN_FILE", str(token_file))

    calls: list[str] = []

    def fake_urlopen(req, timeout: int = 0):
        calls.append(req.get_header("X-vault-token") or "")
        return _FakeVaultResponse('{"data":{"data":{"shared_key":"shared-from-vault"}}}')

    monkeypatch.setattr("app.secrets.request.urlopen", fake_urlopen)

    resolver = SecretResolver()

    assert resolver.resolve("${vault:secret/data/learn-new#shared_key}") == "shared-from-vault"
    assert resolver.resolve("${vault:secret/data/learn-new#shared_key}") == "shared-from-vault"
    assert calls == ["token-from-file"]
