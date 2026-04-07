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
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
            ]
        ),
        encoding="utf-8",
    )


def test_dashboard_route_serves_frontend_split_notice(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_dashboard_config(config_path)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Frontend Workspace" in response.text
    assert "frontend/" in response.text
    assert "npm install" in response.text
    assert "npm run dev" in response.text
    assert "http://127.0.0.1:5173" in response.text
    assert "user.html" in response.text
    assert "admin.html" in response.text
    assert "/api/sessions" in response.text
    assert "/api/tasks/turns" in response.text


def test_frontend_vue_workspace_exists_with_dual_entries_and_split_apps() -> None:
    package_json = Path("frontend/package.json").read_text(encoding="utf-8")
    vite_config = Path("frontend/vite.config.js").read_text(encoding="utf-8")
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")
    user_html = Path("frontend/user.html").read_text(encoding="utf-8")
    admin_html = Path("frontend/admin.html").read_text(encoding="utf-8")
    user_main = Path("frontend/src/user-main.js").read_text(encoding="utf-8")
    admin_main = Path("frontend/src/admin-main.js").read_text(encoding="utf-8")
    user_app = Path("frontend/src/apps/user/UserApp.vue").read_text(encoding="utf-8")
    admin_app = Path("frontend/src/apps/admin/AdminApp.vue").read_text(encoding="utf-8")
    api_js = Path("frontend/src/lib/api.js").read_text(encoding="utf-8")
    learner_vue = Path("frontend/src/components/user/LearningWorkspacePanel.vue").read_text(encoding="utf-8")
    tasks_vue = Path("frontend/src/components/admin/TaskConsolePanel.vue").read_text(encoding="utf-8")
    runtime_vue = Path("frontend/src/components/admin/RuntimePulsePanel.vue").read_text(encoding="utf-8")

    assert '"vue"' in package_json
    assert '"vite"' in package_json
    assert '"@vitejs/plugin-vue"' in package_json
    assert '"dev"' in package_json
    assert '"dev:user"' in package_json
    assert '"dev:admin"' in package_json
    assert '"build"' in package_json
    assert '"build:user"' in package_json
    assert '"build:admin"' in package_json
    assert "defineConfig" in vite_config
    assert "pluginVue" in vite_config
    assert "user.html" in vite_config
    assert "admin.html" in vite_config
    assert "'/api'" in vite_config or '"/api"' in vite_config
    assert "'/ws'" in vite_config or '"/ws"' in vite_config
    assert "127.0.0.1:8000" in vite_config
    assert "user.html" in index_html
    assert "admin.html" in index_html
    assert 'id="app"' in user_html
    assert 'id="app"' in admin_html
    assert "createApp" in user_main
    assert "createApp" in admin_main
    assert "UserApp.vue" in user_main
    assert "AdminApp.vue" in admin_main
    assert "LearningWorkspacePanel" in user_app
    assert "TaskConsolePanel" in admin_app
    assert "RuntimePulsePanel" in admin_app
    assert "X-Admin-Key" not in user_app
    assert "X-Admin-Key" in admin_app
    assert "latest_feedback" in learner_vue
    assert "TaskConsolePanel" in tasks_vue
    assert "new WebSocket" in api_js
    assert "/api/tasks/turns" in api_js
    assert "/api/runtime/summary" in api_js
    assert "RuntimePulsePanel" in runtime_vue
