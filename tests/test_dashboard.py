from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _write_dashboard_config(path: Path) -> None:
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
                "    openai:",
                "      enabled: true",
                "      base_url: https://api.openai.com/v1",
                "      api_key:",
                "      models:",
                "        reasoning: gpt-5.1",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
                "      research:",
                "        provider: openai",
                "        model: gpt-5.1",
                "tasks:",
                "  enabled: true",
                "  worker_threads: 1",
                "  max_queue_size: 8",
            ]
        ),
        encoding="utf-8",
    )


def test_dashboard_page_serves_modern_app_shell_and_frontend_entrypoints(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_dashboard_config(config_path)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="app-shell"' in response.text
    assert 'data-dashboard-version="2"' in response.text
    assert 'href="/static/dashboard.css"' in response.text
    assert 'src="/static/dashboard.js"' in response.text
    assert "Learning Operations Center" in response.text
    assert "Async Task Console" in response.text
    assert "Dead Letter Queue" in response.text
    assert "Runtime Pulse" in response.text
    assert "Knowledge Pipeline" in response.text
    assert "Session Workspace" in response.text
    assert "Provider Routing" in response.text
    assert "domain-input" in response.text
    assert "goal-input" in response.text
    assert "admin-key-input" in response.text
    assert "background-input" in response.text
    assert "time-budget-input" in response.text
    assert "preferences-input" in response.text
    assert "knowledge-url-input" in response.text
    assert "knowledge-title-input" in response.text
    assert "knowledge-content-input" in response.text
    assert "knowledge-source-input" in response.text
    assert "knowledge-query-input" in response.text
    assert "task-answer-input" in response.text
    assert "task-stream-status" in response.text
    assert "dead-letter-list" in response.text
    assert "runtime-summary-panel" in response.text
    assert "config-summary-panel" in response.text
    assert "session-files-panel" in response.text
    assert "due-review-list" in response.text
    assert "knowledge-results" in response.text
    assert "load-export-preview" in response.text
    assert "export-preview" in response.text
    assert "latest-feedback" in response.text
    assert "X-Admin-Key" in response.text
    assert "answer-input" in response.text
    assert "Queue Turn Task" in response.text
    assert "Run Sync Turn" in response.text
    assert "Import URL" in response.text
    assert "Refresh Runtime" in response.text
    assert "Load Config" in response.text


def test_dashboard_static_assets_reference_async_task_and_runtime_apis(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_dashboard_config(config_path)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    css = client.get("/static/dashboard.css")
    js = client.get("/static/dashboard.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert ".task-stream" in css.text
    assert ".runtime-grid" in css.text
    assert ".workspace-tree" in css.text

    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
    assert "/api/sessions" in js.text
    assert "/api/tasks/turns" in js.text
    assert "/api/tasks/dead-letter" in js.text
    assert "/ws/tasks/" in js.text
    assert "/requeue" in js.text
    assert "/api/runtime/summary" in js.text
    assert "/api/config" in js.text
    assert "/api/audit" in js.text
    assert "/api/logs/app" in js.text
    assert "/summary" in js.text
    assert "/timeline" in js.text
    assert "/reviews" in js.text
    assert "/reviews/due" in js.text
    assert "/checkpoints" in js.text
    assert "/knowledge/search" in js.text
    assert "/knowledge/import-url" in js.text
    assert "/export" in js.text
    assert "new WebSocket" in js.text
    assert "renderRuntimeSummary" in js.text
    assert "renderConfigSummary" in js.text
    assert "renderSessionWorkspace" in js.text
