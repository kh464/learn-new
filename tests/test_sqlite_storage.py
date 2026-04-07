import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _write_config(path: Path, sqlite_path: Path) -> None:
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
                "storage:",
                "  backend: sqlite",
                f"  sqlite_path: {sqlite_path.as_posix()}",
            ]
        ),
        encoding="utf-8",
    )


def test_api_reads_session_from_sqlite_store_when_file_snapshot_is_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    sqlite_path = tmp_path / "app.db"
    _write_config(config_path, sqlite_path)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    created = client.post(
        "/api/sessions",
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    state_path = tmp_path / ".learn" / "sessions" / session_id / "state.json"
    state_path.unlink()

    loaded = client.get(f"/api/sessions/{session_id}")
    assert loaded.status_code == 200
    assert loaded.json()["session_id"] == session_id

    listed = client.get("/api/sessions")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_api_restores_checkpoint_from_sqlite_store_when_checkpoint_files_are_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    sqlite_path = tmp_path / "app.db"
    _write_config(config_path, sqlite_path)
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    client = TestClient(app)

    created = client.post(
        "/api/sessions",
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    session_id = created.json()["session_id"]

    turn = client.post(
        f"/api/sessions/{session_id}/turns",
        json={"learner_answer": "asyncio lets coroutines yield while waiting on IO."},
    )
    assert turn.status_code == 200

    checkpoint_dir = tmp_path / ".learn" / "sessions" / session_id / "checkpoints"
    shutil.rmtree(checkpoint_dir)

    listed = client.get(f"/api/sessions/{session_id}/checkpoints")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) >= 1

    checkpoint_id = listed.json()["items"][0]["checkpoint_id"]
    restored = client.post(f"/api/sessions/{session_id}/checkpoints/{checkpoint_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["session_id"] == session_id
