from pathlib import Path

from app.agents.curriculum import CurriculumArchitectAgent
from app.agents.research import ResearcherAgent
from app.knowledge import KnowledgeService
from app.models import LearnerProfile, LearnerState
from app.workspace import WorkspaceManager


def test_researcher_absorbs_user_uploaded_knowledge(tmp_path: Path) -> None:
    manager = WorkspaceManager(root=tmp_path / ".learn")
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    manager.bootstrap_session(state)
    KnowledgeService(manager).ingest_text(
        session_id=state.session_id,
        title="User Notes",
        content="event loop 会调度协程，backpressure 用来控制任务洪峰。",
        source="user://notes",
    )

    updated = ResearcherAgent().run(state, manager)

    assert any(item.source == "user://notes" for item in updated.knowledge_items)
    assert any("backpressure" in item.summary.lower() for item in updated.knowledge_items)


def test_curriculum_includes_keywords_from_uploaded_knowledge(tmp_path: Path) -> None:
    manager = WorkspaceManager(root=tmp_path / ".learn")
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    manager.bootstrap_session(state)
    KnowledgeService(manager).ingest_text(
        session_id=state.session_id,
        title="Advanced Notes",
        content="需要重点理解 event loop、backpressure、task cancellation。",
        source="user://notes",
    )

    updated = CurriculumArchitectAgent().run(state, manager)

    joined_concepts = " ".join(
        concept.lower()
        for stage in updated.curriculum.stages
        for concept in stage.concepts
    )
    assert "event loop" in joined_concepts
    assert "backpressure" in joined_concepts
