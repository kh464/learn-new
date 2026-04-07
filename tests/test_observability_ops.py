from pathlib import Path
import json

from fastapi.testclient import TestClient

from app import runtime_health
from app.main import create_app


def test_metrics_include_path_labels_and_runtime_summary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_health, "_probe_qdrant", lambda base_url: None)
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
                "security:",
                "  enabled: true",
                "  api_key_header: X-Admin-Key",
                "  principals:",
                "    - name: admin",
                "      api_key: admin-key",
                "      role: admin",
                "observability:",
                "  metrics_enabled: true",
                "  request_id_header: X-Request-ID",
                "  audit_log_path: " + (tmp_path / ".learn" / "audit" / "events.jsonl").as_posix(),
                "knowledge:",
                "  backend: qdrant",
                "  qdrant_url: http://qdrant:6333",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    config_response = client.get("/api/config", headers={"X-Admin-Key": "admin-key"})
    assert config_response.status_code == 200

    metrics = client.get("/metrics", headers={"X-Admin-Key": "admin-key"})
    assert metrics.status_code == 200
    assert 'learn_new_requests_by_path_total{path="/api/config",status="200"}' in metrics.text

    summary = client.get("/api/runtime/summary", headers={"X-Admin-Key": "admin-key"})
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["metrics"]["request_count"] >= 2
    assert payload["checks"]["knowledge"]["healthy"] is True
    assert payload["backends"]["knowledge"] == "qdrant"
    assert payload["backends"]["security"] == "enabled"
    assert payload["security"]["principal_count"] == 1
    assert payload["sessions"]["total"] == 0
    assert payload["app_logs"]["enabled"] is True
    assert payload["app_logs"]["recent_count"] == 0


def test_unhandled_errors_return_request_id_and_are_written_to_app_log(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    app_log_path = tmp_path / ".learn" / "logs" / "app.jsonl"
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
                "security:",
                "  enabled: true",
                "  api_key_header: X-Admin-Key",
                "  principals:",
                "    - name: admin",
                "      api_key: admin-key",
                "      role: admin",
                "observability:",
                "  metrics_enabled: true",
                "  request_id_header: X-Request-ID",
                "  audit_log_path: " + (tmp_path / ".learn" / "audit" / "events.jsonl").as_posix(),
                "  app_log_path: " + app_log_path.as_posix(),
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    app.state.orchestrator.list_sessions = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/runtime/summary", headers={"X-Admin-Key": "admin-key"})

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == "Internal Server Error"
    assert payload["request_id"]
    assert response.headers["X-Request-ID"] == payload["request_id"]
    lines = app_log_path.read_text(encoding="utf-8").splitlines()
    assert lines
    item = json.loads(lines[-1])
    assert item["event"] == "unhandled_exception"
    assert item["request_id"] == payload["request_id"]
    assert item["path"] == "/api/runtime/summary"
    assert "boom" in item["error"]


def test_admin_can_read_recent_app_logs(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    app_log_path = tmp_path / ".learn" / "logs" / "app.jsonl"
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
                "security:",
                "  enabled: true",
                "  api_key_header: X-Admin-Key",
                "  principals:",
                "    - name: viewer",
                "      api_key: viewer-key",
                "      role: viewer",
                "    - name: admin",
                "      api_key: admin-key",
                "      role: admin",
                "observability:",
                "  metrics_enabled: true",
                "  request_id_header: X-Request-ID",
                "  app_log_path: " + app_log_path.as_posix(),
            ]
        ),
        encoding="utf-8",
    )
    app_log_path.parent.mkdir(parents=True, exist_ok=True)
    app_log_path.write_text(
        "\n".join(
            [
                json.dumps({"event": "startup", "request_id": "boot", "path": "-", "error": ""}),
                json.dumps({"event": "unhandled_exception", "request_id": "req-1", "path": "/api/runtime/summary", "error": "RuntimeError('boom')"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    denied = client.get("/api/logs/app", headers={"X-Admin-Key": "viewer-key"})
    allowed = client.get("/api/logs/app?limit=1", headers={"X-Admin-Key": "admin-key"})

    assert denied.status_code == 403
    assert allowed.status_code == 200
    payload = allowed.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event"] == "unhandled_exception"
