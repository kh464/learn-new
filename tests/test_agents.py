from app.agents.instructor import InstructorAgent
from app.agents.practice import PracticeEvaluatorAgent
from app.agents.research import ResearcherAgent
from app.agents.skillforge import SkillForgeAgent
from app.models import LearnerProfile, LearnerState
from app.workspace import WorkspaceManager


def test_agents_generate_learning_artifacts(tmp_path) -> None:
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    manager = WorkspaceManager(root=tmp_path / ".learn")
    manager.bootstrap_session(state)

    state = ResearcherAgent().run(state, manager)
    state = SkillForgeAgent().run(state, manager)
    state = InstructorAgent().run(state, manager)
    state = PracticeEvaluatorAgent().run(state, manager)

    assert state.knowledge_items
    assert state.active_skills
    assert state.lesson is not None
    assert state.practice is not None
