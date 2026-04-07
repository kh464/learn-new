from pathlib import Path

from app.knowledge import KnowledgeService
from app.agents.instructor import InstructorAgent
from app.models import Curriculum, CurriculumStage, LearnerProfile, LearnerState
from app.workspace import WorkspaceManager


def test_knowledge_service_ingests_and_retrieves_chunks(tmp_path: Path) -> None:
    manager = WorkspaceManager(root=tmp_path / ".learn")
    state = LearnerState.new(
        domain="Python 异步编程",
        profile=LearnerProfile(goal="掌握 async/await"),
    )
    manager.bootstrap_session(state)
    service = KnowledgeService(manager)

    service.ingest_text(
        session_id=state.session_id,
        title="Event Loop Notes",
        content="事件循环负责调度协程。asyncio.create_task 可以并发安排多个任务。",
        source="user://notes",
    )
    results = service.retrieve(
        session_id=state.session_id,
        query="create_task 如何调度任务",
        limit=1,
    )

    assert len(results) == 1
    assert "create_task" in results[0].content
    assert (tmp_path / ".learn" / "sessions" / state.session_id / "user_uploads" / "Event Loop Notes.txt").exists()


def test_instructor_uses_retrieved_knowledge_in_fallback_lesson(tmp_path: Path) -> None:
    manager = WorkspaceManager(root=tmp_path / ".learn")
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
                concepts=["event loop"],
                practice_format="quiz",
                exit_criteria="能解释事件循环",
            )
        ],
    )
    manager.bootstrap_session(state)
    service = KnowledgeService(manager)
    service.ingest_text(
        session_id=state.session_id,
        title="Event Loop Notes",
        content="event loop 负责在单线程内调度多个协程任务。",
        source="user://notes",
    )

    updated = InstructorAgent().run(state, manager)

    assert updated.lesson is not None
    assert "event loop 负责在单线程内调度多个协程任务" in updated.lesson.explanation
