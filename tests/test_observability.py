from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import LearnerProfile, MasteryRecord
from app.orchestrator import LearningOrchestrator


def test_orchestrator_builds_session_summary_and_timeline(tmp_path: Path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    state = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    state.assessment_score = 88
    state.teaching_mode = "review"
    state.mastery_matrix["event loop"] = MasteryRecord(
        score=88,
        reviews=3,
        interval_days=4,
        next_due=datetime.now(UTC) - timedelta(minutes=1),
        confidence_score=0.88,
    )
    state.add_log("review_started", "Started review for event loop.")
    orchestrator.workspace.save_state(state)

    summary = orchestrator.get_session_summary(state.session_id)
    timeline = orchestrator.get_session_timeline(state.session_id, limit=5)

    assert summary["teaching_mode"] == "review"
    assert summary["due_review_count"] == 1
    assert summary["mastery_overview"]["tracked_concepts"] == 1
    assert timeline["items"][-1]["kind"] == "review_started"


def test_api_exposes_summary_and_timeline(tmp_path: Path) -> None:
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

    orchestrator: LearningOrchestrator = app.state.orchestrator
    state = orchestrator.get_state(session_id)
    state.mastery_matrix["asyncio"] = MasteryRecord(
        score=72,
        reviews=2,
        interval_days=2,
        next_due=datetime.now(UTC) + timedelta(days=1),
        confidence_score=0.72,
    )
    state.add_log("lesson_generated", "Prepared lesson for stage 1.")
    orchestrator.workspace.save_state(state)

    summary = client.get(f"/api/sessions/{session_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["mastery_overview"]["tracked_concepts"] == 1

    timeline = client.get(f"/api/sessions/{session_id}/timeline", params={"limit": 3})
    assert timeline.status_code == 200
    assert len(timeline.json()["items"]) >= 1
