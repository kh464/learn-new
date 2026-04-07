from datetime import UTC, datetime, timedelta

from app.agents.curriculum import CurriculumArchitectAgent
from app.agents.progress import ProgressMonitorAgent
from app.models import LearnerProfile, LearnerState


def test_progress_monitor_schedules_longer_review_for_high_scores() -> None:
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    curriculum_agent = CurriculumArchitectAgent()
    progress_agent = ProgressMonitorAgent()
    state.domain_meta = curriculum_agent.analyze_domain(state.domain)
    state.curriculum = curriculum_agent.build_curriculum(state.domain, state.domain_meta)

    state.assessment_score = 95
    updated = progress_agent.update_progress(state)
    concept = updated.curriculum.stages[0].concepts[0]
    record = updated.mastery_matrix[concept]

    assert record.interval_days >= 3
    assert record.next_due > datetime.now(UTC) + timedelta(days=2)
    assert updated.current_stage == 2


def test_progress_monitor_triggers_intervention_after_two_low_scores() -> None:
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    curriculum_agent = CurriculumArchitectAgent()
    progress_agent = ProgressMonitorAgent()
    state.domain_meta = curriculum_agent.analyze_domain(state.domain)
    state.curriculum = curriculum_agent.build_curriculum(state.domain, state.domain_meta)

    state.assessment_score = 45
    state = progress_agent.update_progress(state)
    assert state.needs_intervention is False
    assert state.consecutive_low_scores == 1

    state.assessment_score = 40
    state = progress_agent.update_progress(state)

    assert state.needs_intervention is True
    assert state.teaching_mode == "remedial"
    assert state.consecutive_low_scores == 2
    assert any(log.kind == "intervention" for log in state.logs)
