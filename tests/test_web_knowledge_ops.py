from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_import_knowledge_from_url_ingests_remote_text(tmp_path: Path) -> None:
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
    app.state.web_fetcher = lambda url: {
        "title": "Async Notes",
        "content": "asyncio.create_task schedules concurrent coroutines.",
        "source": url,
    }
    client = TestClient(app)

    created = client.post(
        "/api/sessions",
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    session_id = created.json()["session_id"]

    imported = client.post(
        f"/api/sessions/{session_id}/knowledge/import-url",
        json={"url": "https://example.com/async"},
    )
    searched = client.get(
        f"/api/sessions/{session_id}/knowledge/search",
        params={"query": "create_task concurrent coroutines"},
    )

    assert imported.status_code == 201
    assert imported.json()["chunks_added"] >= 1
    assert searched.status_code == 200
    assert searched.json()["items"][0]["source"] == "https://example.com/async"
