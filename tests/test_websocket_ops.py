from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _write_websocket_config(path: Path) -> None:
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
                "  enabled: true",
                "  api_key_header: X-Admin-Key",
                "  principals:",
                "    - name: alice",
                "      api_key: alice-key",
                "      role: operator",
                "    - name: root",
                "      api_key: root-key",
                "      role: admin",
                "tasks:",
                "  enabled: true",
                "  worker_threads: 1",
                "  max_queue_size: 8",
            ]
        ),
        encoding="utf-8",
    )


def test_task_websocket_streams_status_updates_until_completion(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_websocket_config(config_path)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)

    with TestClient(app) as client:
        created = client.post(
            "/api/sessions",
            headers={"X-Admin-Key": "alice-key"},
            json={"domain": "Python async programming", "goal": "Master async/await"},
        )
        session_id = created.json()["session_id"]

        task_response = client.post(
            "/api/tasks/turns",
            headers={"X-Admin-Key": "alice-key"},
            json={"session_id": session_id, "learner_answer": "event loop schedules concurrent coroutines"},
        )
        task_id = task_response.json()["task_id"]

        with client.websocket_connect(f"/ws/tasks/{task_id}", headers={"X-Admin-Key": "alice-key"}) as websocket:
            statuses = []
            while True:
                message = websocket.receive_json()
                statuses.append(message["status"])
                if message["status"] == "completed":
                    assert message["result"]["session_id"] == session_id
                    break

        assert "queued" in statuses or "running" in statuses
        assert statuses[-1] == "completed"
