from pathlib import Path

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
