from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from app.main import create_app


def _write_task_config(path: Path) -> None:
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
                "    - name: bob",
                "      api_key: bob-key",
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


def test_async_turn_task_can_be_enqueued_and_completed(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_task_config(config_path)
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
            json={"session_id": session_id, "learner_answer": "asyncio lets IO wait without blocking the main flow"},
        )

        assert task_response.status_code == 202
        task_id = task_response.json()["task_id"]

        payload = None
        for _ in range(40):
            lookup = client.get(f"/api/tasks/{task_id}", headers={"X-Admin-Key": "alice-key"})
            assert lookup.status_code == 200
            payload = lookup.json()
            if payload["status"] == "completed":
                break
            sleep(0.05)

        assert payload is not None
        assert payload["status"] == "completed"
        assert payload["result"]["session_id"] == session_id
        assert payload["result"]["log_count"] >= 2


def test_task_visibility_is_limited_to_owner_unless_admin(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    _write_task_config(config_path)
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
            json={"session_id": session_id, "learner_answer": "event loop schedules work"},
        )
        task_id = task_response.json()["task_id"]

        denied = client.get(f"/api/tasks/{task_id}", headers={"X-Admin-Key": "bob-key"})
        allowed = client.get(f"/api/tasks/{task_id}", headers={"X-Admin-Key": "root-key"})

        assert denied.status_code == 404
        assert allowed.status_code == 200

        for _ in range(40):
            lookup = client.get(f"/api/tasks/{task_id}", headers={"X-Admin-Key": "root-key"})
            if lookup.json()["status"] in {"completed", "failed"}:
                break
            sleep(0.05)
