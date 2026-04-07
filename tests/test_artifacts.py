from pathlib import Path

from app.models import LearnerProfile
from app.orchestrator import LearningOrchestrator


def test_session_writes_core_learn_artifacts(tmp_path: Path) -> None:
    orchestrator = LearningOrchestrator(workspace_root=tmp_path / ".learn")
    state = orchestrator.create_session(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    updated = orchestrator.run_turn(
        session_id=state.session_id,
        learner_answer="asyncio 可以调度协程，因为它适合 IO 密集场景，并且我会用 create_task 组织任务。",
    )

    session_dir = tmp_path / ".learn" / "sessions" / updated.session_id

    assert (session_dir / "config.yaml").exists()
    assert (session_dir / "domain_meta.json").exists()
    assert (session_dir / "curriculum.md").exists()
    assert (session_dir / "lesson.json").exists()
