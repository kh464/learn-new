from pathlib import Path

from app.agents.instructor import InstructorAgent
from app.models import Curriculum, CurriculumStage, LearnerProfile, LearnerState
from app.workspace import WorkspaceManager


def test_instructor_switches_to_remedial_explanation_when_intervention_needed(tmp_path: Path) -> None:
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    state.curriculum = Curriculum(
        domain=state.domain,
        stages=[
            CurriculumStage(
                stage=1,
                title="入门",
                objective="理解事件循环",
                concepts=["event loop", "asyncio"],
                practice_format="quiz",
                exit_criteria="能解释事件循环",
            )
        ],
    )
    state.teaching_mode = "remedial"
    state.needs_intervention = True
    state.review_queue = ["event loop"]
    manager = WorkspaceManager(root=tmp_path / ".learn")
    manager.bootstrap_session(state)

    updated = InstructorAgent().run(state, manager)

    assert updated.lesson is not None
    assert "补救" in updated.lesson.explanation
    assert "event loop" in updated.lesson.explanation
