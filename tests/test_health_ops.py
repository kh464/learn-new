from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app import runtime_health


def test_health_ready_reports_runtime_capabilities(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_health, "_probe_docker", lambda: None)
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
                "storage:",
                "  backend: sqlite",
                f"  sqlite_path: {(tmp_path / 'runtime.db').as_posix()}",
                "sandbox:",
                "  backend: docker",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["storage_backend"] == "sqlite"
    assert payload["sandbox_backend"] == "docker"
    assert payload["metrics_enabled"] is True
    assert payload["checks"]["storage"]["healthy"] is True
    assert payload["checks"]["sandbox"]["healthy"] is True


def test_health_ready_returns_503_when_required_backend_probe_fails(tmp_path: Path, monkeypatch) -> None:
    def fail_qdrant(base_url: str) -> None:
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(runtime_health, "_probe_qdrant", fail_qdrant)
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
                "knowledge:",
                "  backend: qdrant",
                "  qdrant_url: http://qdrant:6333",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["checks"]["knowledge"]["healthy"] is False
    assert "qdrant down" in payload["checks"]["knowledge"]["detail"]
