from pathlib import Path

from app.config import load_config


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
