import importlib
from pathlib import Path


def test_module_level_app_respects_config_path_environment(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "llm-env.yaml"
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
                "      api_key:",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
                "storage:",
                "  backend: sqlite",
                f"  sqlite_path: {(tmp_path / 'app.db').as_posix()}",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("LEARN_NEW_CONFIG_PATH", str(config_path))

    import app.main as main_module

    reloaded = importlib.reload(main_module)

    assert reloaded.app.state.config.storage.backend == "sqlite"
