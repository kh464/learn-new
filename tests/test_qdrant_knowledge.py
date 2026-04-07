from pathlib import Path

from app.knowledge import KnowledgeService
from app.vector_store import QdrantKnowledgeIndex
from app.workspace import WorkspaceManager
from app.models import LearnerProfile, LearnerState


class FakeQdrantTransport:
    def __init__(self):
        self.requests = []

    def __call__(self, method: str, url: str, payload: dict | None = None) -> dict:
        self.requests.append((method, url, payload))
        if url.endswith("/collections/learn-new"):
            return {"result": True}
        if url.endswith("/points/search"):
            return {
                "result": [
                    {
                        "id": "chunk-1",
                        "score": 0.9,
                        "payload": {
                            "chunk_id": "chunk-1",
                            "title": "Event Loop Notes",
                            "content": "asyncio.create_task schedules concurrent work",
                            "source": "user://notes",
                            "tags": ["asyncio", "create_task"],
                        },
                    }
                ]
            }
        return {"result": {"status": "ok"}}


def test_qdrant_knowledge_index_is_used_for_ingest_and_search(tmp_path: Path) -> None:
    manager = WorkspaceManager(root=tmp_path / ".learn")
    state = LearnerState.new(
        domain="Python async programming",
        profile=LearnerProfile(goal="Master async/await"),
    )
    manager.bootstrap_session(state)
    transport = FakeQdrantTransport()
    manager.knowledge_index = QdrantKnowledgeIndex(
        base_url="http://qdrant:6333",
        collection_name="learn-new",
        transport=transport,
    )
    service = KnowledgeService(manager)

    service.ingest_text(
        session_id=state.session_id,
        title="Event Loop Notes",
        content="asyncio.create_task schedules concurrent work",
        source="user://notes",
    )
    results = service.retrieve(session_id=state.session_id, query="create_task concurrent work", limit=1)

    assert len(results) == 1
    assert results[0].chunk_id == "chunk-1"
    assert any("/collections/learn-new/points" in request[1] for request in transport.requests)
    assert any("/collections/learn-new/points/search" in request[1] for request in transport.requests)
