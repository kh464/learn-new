from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import LearnerProfile
from app.orchestrator import LearningOrchestrator


def test_orchestrator_exports_session_bundle(tmp_path: Path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    state = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    orchestrator.run_turn(
        session_id=state.session_id,
        learner_answer="我会用 asyncio.create_task，因为它适合调度任务场景。",
    )

    exported = orchestrator.export_session(state.session_id)

    assert exported["session"]["session_id"] == state.session_id
    assert "summary" in exported
    assert "timeline" in exported
    assert "artifacts" in exported
    assert "curriculum_markdown" in exported["artifacts"]
    assert "state" in exported["artifacts"]


def test_api_exports_session_bundle(tmp_path: Path) -> None:
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

    exported = client.get(f"/api/sessions/{session_id}/export")

    assert exported.status_code == 200
    assert exported.json()["session"]["session_id"] == session_id
    assert "timeline" in exported.json()
