from app.agents.curriculum import CurriculumArchitectAgent
from app.agents.progress import ProgressMonitorAgent
from app.models import LearnerProfile, LearnerState


def test_curriculum_has_five_stages_and_progress_advances_on_high_score() -> None:
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    curriculum_agent = CurriculumArchitectAgent()
    progress_agent = ProgressMonitorAgent()

    state.domain_meta = curriculum_agent.analyze_domain(state.domain)
    state.curriculum = curriculum_agent.build_curriculum(state.domain, state.domain_meta)
    state.assessment_score = 92

    updated = progress_agent.update_progress(state)

    assert len(updated.curriculum.stages) == 5
    assert updated.current_stage == 2
