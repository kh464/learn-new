from fastapi.testclient import TestClient

from app.main import create_app


def test_api_creates_session_and_runs_turn(tmp_path) -> None:
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

    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    assert isinstance(config_response.json()["llm_available"], bool)
    assert config_response.json()["llm_available"] is False

    response = client.post(
        "/api/sessions",
        json={"domain": "Python 异步编程", "goal": "掌握 async/await"},
    )
    assert response.status_code == 201
    session_id = response.json()["session_id"]

    knowledge = client.post(
        f"/api/sessions/{session_id}/knowledge",
        json={
            "title": "Async Notes",
            "content": "asyncio.create_task 可以并发调度多个协程任务。",
            "source": "user://manual",
        },
    )
    assert knowledge.status_code == 201
    assert knowledge.json()["chunks_added"] >= 1

    search = client.get(
        f"/api/sessions/{session_id}/knowledge/search",
        params={"query": "create_task 调度任务"},
    )
    assert search.status_code == 200
    assert len(search.json()["items"]) >= 1

    turn = client.post(
        f"/api/sessions/{session_id}/turns",
        json={"learner_answer": "我会用 asyncio.create_task"},
    )
    assert turn.status_code == 200
    assert "lesson" in turn.json()
    assert "create_task" in turn.json()["lesson"]["explanation"] or "asyncio.create_task" in turn.json()["lesson"]["explanation"]
