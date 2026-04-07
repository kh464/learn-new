from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import LearnerProfile
from app.orchestrator import LearningOrchestrator


def test_orchestrator_lists_sessions_with_summary(tmp_path: Path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    first = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    second = orchestrator.create_session(
        domain="Rust 高性能编程",
        profile=LearnerProfile(goal="理解所有权与并发"),
    )
    orchestrator.run_turn(
        session_id=first.session_id,
        learner_answer="我会用 asyncio.create_task，因为它适合调度任务场景。",
    )

    payload = orchestrator.list_sessions()

    assert payload["total"] == 2
    assert payload["items"][0]["session_id"] in {first.session_id, second.session_id}
    assert all("summary" in item for item in payload["items"])


def test_api_lists_sessions_for_dashboard(tmp_path: Path) -> None:
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

    first = client.post(
        "/api/sessions",
        json={"domain": "Python 异步编程", "goal": "掌握 async/await"},
    ).json()
    second = client.post(
        "/api/sessions",
        json={"domain": "Rust 高性能编程", "goal": "理解所有权与并发"},
    ).json()
    client.post(
        f"/api/sessions/{first['session_id']}/turns",
        json={"learner_answer": "我会用 asyncio.create_task，因为它适合调度任务场景。"},
    )

    listed = client.get("/api/sessions")

    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    ids = {item["session_id"] for item in listed.json()["items"]}
    assert ids == {first["session_id"], second["session_id"]}
