from pathlib import Path

from app.main import create_app


class CapturingPostgresTaskQueue:
    last_kwargs = None

    def __init__(self, **kwargs):
        CapturingPostgresTaskQueue.last_kwargs = kwargs

    def start(self) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def snapshot(self) -> dict:
        return {"backend": "postgres"}


def test_create_app_passes_lease_settings_to_postgres_task_queue(tmp_path: Path, monkeypatch) -> None:
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
                "      api_key:",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
                "tasks:",
                "  enabled: true",
                "  backend: postgres",
                "  postgres_dsn: postgresql://learn-new:secret@db/learn_new",
                "  worker_threads: 2",
                "  max_attempts: 4",
                "  lease_seconds: 45",
                "  poll_interval_seconds: 0.25",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.main.PostgresTaskQueue", CapturingPostgresTaskQueue)

    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)

    assert app.state.task_queue is not None
    assert CapturingPostgresTaskQueue.last_kwargs is not None
    assert CapturingPostgresTaskQueue.last_kwargs["lease_seconds"] == 45
    assert CapturingPostgresTaskQueue.last_kwargs["poll_interval_seconds"] == 0.25
