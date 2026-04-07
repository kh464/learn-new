from app.models import LearnerProfile
from app.orchestrator import LearningOrchestrator


def test_orchestrator_runs_one_turn(tmp_path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    state = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )

    updated = orchestrator.run_turn(
        session_id=state.session_id,
        learner_answer="asyncio 用于调度协程",
    )

    assert updated.lesson is not None
    assert updated.practice is not None
    assert updated.logs
