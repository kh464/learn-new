from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _write_config(
    path: Path,
    *,
    security_enabled: bool = False,
    api_key: str = "secret-key",
    rate_limit_enabled: bool = False,
    requests: int = 60,
    window_seconds: int = 60,
) -> None:
    path.write_text(
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
                f"  enabled: {'true' if security_enabled else 'false'}",
                "  api_key_header: X-Admin-Key",
                f"  api_key: {api_key}",
                "rate_limit:",
                f"  enabled: {'true' if rate_limit_enabled else 'false'}",
                f"  requests: {requests}",
                f"  window_seconds: {window_seconds}",
                "observability:",
                "  metrics_enabled: true",
                "  request_id_header: X-Request-ID",
            ]
        ),
        encoding="utf-8",
    )


def test_api_requires_admin_key_when_security_is_enabled(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_config(config_path, security_enabled=True)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200

    denied = client.get("/api/config")
    assert denied.status_code == 401
    assert denied.headers["X-Request-ID"]

    allowed = client.get("/api/config", headers={"X-Admin-Key": "secret-key"})
    assert allowed.status_code == 200
    assert allowed.headers["X-Request-ID"]


def test_api_rate_limits_repeated_requests_and_exposes_metrics(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_config(config_path, rate_limit_enabled=True, requests=1, window_seconds=60)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    first = client.get("/api/config")
    assert first.status_code == 200
    assert first.headers["X-Request-ID"]

    second = client.get("/api/config")
    assert second.status_code == 429
    assert second.headers["X-Request-ID"]
    assert second.headers["Retry-After"] == "60"

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "learn_new_requests_total" in metrics.text
    assert "learn_new_request_latency_ms_total" in metrics.text


def test_rate_limit_is_scoped_per_authenticated_principal(tmp_path: Path) -> None:
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
                "    - name: alice",
                "      api_key: alice-key",
                "      role: viewer",
                "    - name: bob",
                "      api_key: bob-key",
                "      role: viewer",
                "    - name: root",
                "      api_key: root-key",
                "      role: admin",
                "rate_limit:",
                "  enabled: true",
                "  requests: 1",
                "  window_seconds: 60",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    alice_first = client.get("/api/config", headers={"X-Admin-Key": "alice-key"})
    bob_first = client.get("/api/config", headers={"X-Admin-Key": "bob-key"})
    alice_second = client.get("/api/config", headers={"X-Admin-Key": "alice-key"})

    assert alice_first.status_code == 200
    assert bob_first.status_code == 200
    assert alice_second.status_code == 429


def test_api_enforces_role_based_tokens_and_exposes_audit_log(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    audit_path = (tmp_path / ".learn" / "audit" / "events.jsonl").as_posix()
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
                "    - name: operator",
                "      api_key: operator-key",
                "      role: operator",
                "    - name: admin",
                "      api_key: admin-key",
                "      role: admin",
                "observability:",
                "  metrics_enabled: true",
                "  request_id_header: X-Request-ID",
                "  audit_log_path: " + audit_path,
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    viewer_config = client.get("/api/config", headers={"X-Admin-Key": "viewer-key"})
    assert viewer_config.status_code == 200

    viewer_write = client.post(
        "/api/sessions",
        headers={"X-Admin-Key": "viewer-key"},
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    assert viewer_write.status_code == 403

    operator_create = client.post(
        "/api/sessions",
        headers={"X-Admin-Key": "operator-key"},
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    assert operator_create.status_code == 201

    operator_metrics = client.get("/metrics", headers={"X-Admin-Key": "operator-key"})
    assert operator_metrics.status_code == 403

    admin_metrics = client.get("/metrics", headers={"X-Admin-Key": "admin-key"})
    assert admin_metrics.status_code == 200

    audit = client.get("/api/audit", headers={"X-Admin-Key": "admin-key"})
    assert audit.status_code == 200
    payload = audit.json()
    assert payload["items"]
    assert any(item["principal"] == "viewer" and item["status_code"] == 403 for item in payload["items"])
    assert any(item["principal"] == "operator" and item["status_code"] == 201 for item in payload["items"])
    assert any(item["principal"] == "admin" and item["path"] == "/metrics" for item in payload["items"])


def test_api_limits_session_visibility_to_owner_unless_admin(tmp_path: Path) -> None:
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
                "    - name: alice",
                "      api_key: alice-key",
                "      role: operator",
                "    - name: bob",
                "      api_key: bob-key",
                "      role: operator",
                "    - name: root",
                "      api_key: root-key",
                "      role: admin",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    created = client.post(
        "/api/sessions",
        headers={"X-Admin-Key": "alice-key"},
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    alice_list = client.get("/api/sessions", headers={"X-Admin-Key": "alice-key"})
    assert alice_list.status_code == 200
    assert alice_list.json()["total"] == 1

    bob_list = client.get("/api/sessions", headers={"X-Admin-Key": "bob-key"})
    assert bob_list.status_code == 200
    assert bob_list.json()["total"] == 0

    bob_get = client.get(f"/api/sessions/{session_id}", headers={"X-Admin-Key": "bob-key"})
    assert bob_get.status_code == 404

    admin_get = client.get(f"/api/sessions/{session_id}", headers={"X-Admin-Key": "root-key"})
    assert admin_get.status_code == 200
