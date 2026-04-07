from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import LearnerProfile, LearnerState, MasteryRecord
from app.orchestrator import LearningOrchestrator


def test_orchestrator_starts_review_for_due_concepts(tmp_path: Path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    state = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    state.mastery_matrix["event loop"] = MasteryRecord(
        score=50,
        reviews=2,
        interval_days=1,
        next_due=datetime.now(UTC) - timedelta(minutes=5),
        confidence_score=0.5,
    )
    orchestrator.workspace.save_state(state)

    updated = orchestrator.start_review(state.session_id)

    assert updated.teaching_mode == "review"
    assert updated.review_queue == ["event loop"]
    assert updated.lesson is not None
    assert "复习" in updated.lesson.explanation


def test_api_exposes_due_reviews_and_review_entry(tmp_path: Path) -> None:
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
    state.mastery_matrix["event loop"] = MasteryRecord(
        score=55,
        reviews=1,
        interval_days=1,
        next_due=datetime.now(UTC) - timedelta(minutes=10),
        confidence_score=0.55,
    )
    orchestrator.workspace.save_state(state)

    due = client.get(f"/api/sessions/{session_id}/reviews/due")
    assert due.status_code == 200
    assert due.json()["items"] == ["event loop"]

    review = client.post(f"/api/sessions/{session_id}/reviews")
    assert review.status_code == 200
    assert review.json()["teaching_mode"] == "review"
    assert "复习" in review.json()["lesson"]["explanation"]
