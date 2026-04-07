from pathlib import Path

from app.task_queue import SQLiteTaskQueue


def test_sqlite_task_queue_persists_completed_tasks_across_restarts(tmp_path: Path) -> None:
    db_path = tmp_path / "tasks.db"
    queue = SQLiteTaskQueue(path=db_path, worker_threads=1, max_queue_size=8)
    task = queue.submit(
        task_type="turn",
        session_id="session-1",
        owner_id="alice",
        runner=lambda: {"session_id": "session-1", "status": "ok"},
    )
    queue.wait(task["task_id"], timeout_seconds=5)
    queue.shutdown()

    reloaded = SQLiteTaskQueue(path=db_path, worker_threads=1, max_queue_size=8)
    restored = reloaded.get(task["task_id"])
    reloaded.shutdown()

    assert restored["status"] == "completed"
    assert restored["result"]["session_id"] == "session-1"
