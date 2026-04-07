from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_dashboard_page_is_served_and_references_core_apis(tmp_path: Path) -> None:
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
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/api/sessions" in response.text
    assert "/summary" in response.text
    assert "/timeline" in response.text
    assert "/reviews" in response.text
    assert "/reviews/due" in response.text
    assert "/checkpoints" in response.text
    assert "/knowledge" in response.text
    assert "/knowledge/search" in response.text
    assert "/export" in response.text
    assert "Start Review" in response.text
    assert "Restore Checkpoint" in response.text
    assert "Create Session" in response.text
    assert "Upload Knowledge" in response.text
    assert "Search Knowledge" in response.text
    assert "Due Review Queue" in response.text
    assert "Session Export Preview" in response.text
    assert "Latest Feedback" in response.text
    assert "domain-input" in response.text
    assert "goal-input" in response.text
    assert "admin-key-input" in response.text
    assert "knowledge-title-input" in response.text
    assert "knowledge-content-input" in response.text
    assert "knowledge-source-input" in response.text
    assert "knowledge-query-input" in response.text
    assert "due-review-list" in response.text
    assert "knowledge-results" in response.text
    assert "load-export-preview" in response.text
    assert "export-preview" in response.text
    assert "latest-feedback" in response.text
    assert "X-Admin-Key" in response.text
    assert "Submit Turn" in response.text
    assert "answer-input" in response.text
    assert "Python async programming" in response.text
    assert "Master async/await" in response.text
