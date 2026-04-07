from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import LearnerProfile
from app.orchestrator import LearningOrchestrator


def test_orchestrator_lists_and_restores_checkpoints(tmp_path: Path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    state = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    first = orchestrator.run_turn(
        session_id=state.session_id,
        learner_answer="我会用 asyncio.create_task，因为它适合调度任务场景。",
    )
    second = orchestrator.run_turn(
        session_id=state.session_id,
        learner_answer="很短",
    )

    checkpoints = orchestrator.list_checkpoints(state.session_id)

    assert len(checkpoints["items"]) >= 2
    target = checkpoints["items"][0]["checkpoint_id"]

    restored = orchestrator.restore_checkpoint(state.session_id, target)

    assert restored.session_id == state.session_id
    assert restored.current_stage <= second.current_stage
    assert any(log.kind == "checkpoint_restored" for log in restored.logs)


def test_api_lists_and_restores_checkpoints(tmp_path: Path) -> None:
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

    created = client.post(
        "/api/sessions",
        json={"domain": "Python 异步编程", "goal": "掌握 async/await"},
    ).json()
    session_id = created["session_id"]
    client.post(
        f"/api/sessions/{session_id}/turns",
        json={"learner_answer": "我会用 asyncio.create_task，因为它适合调度任务场景。"},
    )

    checkpoints = client.get(f"/api/sessions/{session_id}/checkpoints")
    assert checkpoints.status_code == 200
    assert len(checkpoints.json()["items"]) >= 1

    checkpoint_id = checkpoints.json()["items"][0]["checkpoint_id"]
    restored = client.post(f"/api/sessions/{session_id}/checkpoints/{checkpoint_id}/restore")

    assert restored.status_code == 200
    assert restored.json()["session_id"] == session_id
