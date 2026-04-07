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


def test_sqlite_task_queue_retries_failed_tasks_until_success(tmp_path: Path) -> None:
    db_path = tmp_path / "tasks.db"
    attempts = {"count": 0}

    def handler(payload: dict) -> dict:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("transient failure")
        return {"session_id": payload["session_id"], "status": "ok"}

    queue = SQLiteTaskQueue(
        path=db_path,
        worker_threads=1,
        max_queue_size=8,
        max_attempts=2,
        handlers={"turn": handler},
    )
    task = queue.submit(
        task_type="turn",
        session_id="session-1",
        owner_id="alice",
        payload={"session_id": "session-1"},
    )

    completed = queue.wait(task["task_id"], timeout_seconds=5)
    queue.shutdown()

    assert completed["status"] == "completed"
    assert completed["attempt_count"] == 2
    assert completed["result"]["status"] == "ok"


def test_sqlite_task_queue_marks_task_failed_after_retry_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "tasks.db"

    def handler(_payload: dict) -> dict:
        raise RuntimeError("still broken")

    queue = SQLiteTaskQueue(
        path=db_path,
        worker_threads=1,
        max_queue_size=8,
        max_attempts=2,
        handlers={"turn": handler},
    )
    task = queue.submit(
        task_type="turn",
        session_id="session-1",
        owner_id="alice",
        payload={"session_id": "session-1"},
    )

    failed = queue.wait(task["task_id"], timeout_seconds=5)
    queue.shutdown()

    assert failed["status"] == "failed"
    assert failed["attempt_count"] == 2
    assert "still broken" in failed["error"]
