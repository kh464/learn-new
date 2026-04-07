from __future__ import annotations

from datetime import UTC, datetime
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from typing import Callable
from uuid import uuid4


class TaskQueueFullError(RuntimeError):
    pass


class InMemoryTaskQueue:
    def __init__(
        self,
        worker_threads: int = 1,
        max_queue_size: int = 100,
        on_update: Callable[[dict], None] | None = None,
    ) -> None:
        self.worker_threads = worker_threads
        self.on_update = on_update
        self._queue: Queue[dict] = Queue(maxsize=max_queue_size)
        self._stop = Event()
        self._lock = Lock()
        self._tasks: dict[str, dict] = {}
        self._workers: list[Thread] = []
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._stop.clear()
            self._workers = [
                Thread(target=self._worker_loop, name=f"learn-new-task-{index}", daemon=True)
                for index in range(self.worker_threads)
            ]
            for worker in self._workers:
                worker.start()
            self._started = True

    def submit(
        self,
        *,
        task_type: str,
        session_id: str,
        owner_id: str,
        runner: Callable[[], dict],
    ) -> dict:
        self.start()
        task_id = uuid4().hex
        record = {
            "task_id": task_id,
            "task_type": task_type,
            "session_id": session_id,
            "owner_id": owner_id,
            "status": "queued",
            "error": None,
            "result": None,
            "created_at": _utc_iso(),
            "started_at": None,
            "completed_at": None,
            "runner": runner,
        }
        with self._lock:
            self._tasks[task_id] = record
        try:
            self._queue.put_nowait({"task_id": task_id})
        except Full as exc:
            with self._lock:
                self._tasks.pop(task_id, None)
            raise TaskQueueFullError("Task queue is full") from exc
        public = self._public_record(record)
        self._emit(public)
        return public

    def get(self, task_id: str) -> dict:
        with self._lock:
            record = self._tasks.get(task_id)
            if record is None:
                raise FileNotFoundError(task_id)
            return self._public_record(record)

    def snapshot(self) -> dict:
        with self._lock:
            counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
            for record in self._tasks.values():
                counts[record["status"]] = counts.get(record["status"], 0) + 1
            return {
                "worker_threads": self.worker_threads,
                "queue_depth": self._queue.qsize(),
                "counts": counts,
            }

    def shutdown(self) -> None:
        with self._lock:
            if not self._started:
                return
            workers = list(self._workers)
            self._started = False
        self._stop.set()
        for _ in workers:
            self._queue.put({"task_id": None})
        for worker in workers:
            worker.join(timeout=1)

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except Empty:
                continue
            task_id = item.get("task_id")
            if task_id is None:
                self._queue.task_done()
                continue
            with self._lock:
                record = self._tasks.get(task_id)
                if record is None:
                    self._queue.task_done()
                    continue
                record["status"] = "running"
                record["started_at"] = _utc_iso()
                runner = record["runner"]
                public = self._public_record(record)
            self._emit(public)
            try:
                result = runner()
                with self._lock:
                    record["status"] = "completed"
                    record["result"] = result
                    record["completed_at"] = _utc_iso()
                    public = self._public_record(record)
            except Exception as exc:
                with self._lock:
                    record["status"] = "failed"
                    record["error"] = repr(exc)
                    record["completed_at"] = _utc_iso()
                    public = self._public_record(record)
            finally:
                self._emit(public)
                self._queue.task_done()

    def _public_record(self, record: dict) -> dict:
        return {
            "task_id": record["task_id"],
            "task_type": record["task_type"],
            "session_id": record["session_id"],
            "owner_id": record["owner_id"],
            "status": record["status"],
            "error": record["error"],
            "result": record["result"],
            "created_at": record["created_at"],
            "started_at": record["started_at"],
            "completed_at": record["completed_at"],
        }

    def _emit(self, record: dict) -> None:
        if self.on_update is not None:
            self.on_update(record)


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()
