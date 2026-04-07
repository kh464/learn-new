from __future__ import annotations

import importlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from time import monotonic, sleep
from typing import Callable, Iterator
from uuid import uuid4


class TaskQueueFullError(RuntimeError):
    pass


TaskHandler = Callable[[dict], dict]


class InMemoryTaskQueue:
    def __init__(
        self,
        worker_threads: int = 1,
        max_queue_size: int = 100,
        max_attempts: int = 1,
        on_update: Callable[[dict], None] | None = None,
        handlers: dict[str, TaskHandler] | None = None,
    ) -> None:
        self.worker_threads = worker_threads
        self.max_attempts = max_attempts
        self.on_update = on_update
        self.handlers = handlers or {}
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
        payload: dict | None = None,
        runner: Callable[[], dict] | None = None,
    ) -> dict:
        self.start()
        task_id = uuid4().hex
        record = {
            "task_id": task_id,
            "task_type": task_type,
            "session_id": session_id,
            "owner_id": owner_id,
            "payload": payload or {},
            "status": "queued",
            "error": None,
            "result": None,
            "created_at": _utc_iso(),
            "started_at": None,
            "completed_at": None,
            "attempt_count": 0,
            "max_attempts": self.max_attempts,
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

    def wait(self, task_id: str, timeout_seconds: float = 5.0) -> dict:
        deadline = monotonic() + timeout_seconds
        while monotonic() < deadline:
            record = self.get(task_id)
            if record["status"] in {"completed", "failed"}:
                return record
            sleep(0.05)
        raise TimeoutError(task_id)

    def snapshot(self) -> dict:
        with self._lock:
            counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
            for record in self._tasks.values():
                counts[record["status"]] = counts.get(record["status"], 0) + 1
            return {
                "backend": "memory",
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
                record["attempt_count"] += 1
                record["started_at"] = _utc_iso()
                public = self._public_record(record)
            self._emit(public)
            try:
                result = self._execute(record)
                with self._lock:
                    record["status"] = "completed"
                    record["result"] = result
                    record["completed_at"] = _utc_iso()
                    public = self._public_record(record)
            except Exception as exc:
                with self._lock:
                    record["error"] = repr(exc)
                    if record["attempt_count"] < record["max_attempts"]:
                        record["status"] = "queued"
                        record["completed_at"] = None
                        public = self._public_record(record)
                        self._queue.put({"task_id": task_id})
                    else:
                        record["status"] = "failed"
                        record["completed_at"] = _utc_iso()
                        public = self._public_record(record)
            finally:
                self._emit(public)
                self._queue.task_done()

    def _execute(self, record: dict) -> dict:
        if record["runner"] is not None:
            return record["runner"]()
        handler = self.handlers.get(record["task_type"])
        if handler is None:
            raise RuntimeError(f"No handler registered for task type '{record['task_type']}'")
        return handler(record["payload"])

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
            "attempt_count": record["attempt_count"],
            "max_attempts": record["max_attempts"],
        }

    def _emit(self, record: dict) -> None:
        if self.on_update is not None:
            self.on_update(record)


class SQLiteTaskQueue(InMemoryTaskQueue):
    def __init__(
        self,
        path: Path | str,
        worker_threads: int = 1,
        max_queue_size: int = 100,
        max_attempts: int = 1,
        on_update: Callable[[dict], None] | None = None,
        handlers: dict[str, TaskHandler] | None = None,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(
            worker_threads=worker_threads,
            max_queue_size=max_queue_size,
            max_attempts=max_attempts,
            on_update=on_update,
            handlers=handlers,
        )
        self._initialize()
        self._load_existing_tasks()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS task_queue (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_queue_status_created_at ON task_queue(status, created_at)"
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(task_queue)").fetchall()
            }
            if "attempt_count" not in columns:
                connection.execute("ALTER TABLE task_queue ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
            if "max_attempts" not in columns:
                connection.execute("ALTER TABLE task_queue ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 1")

    def _load_existing_tasks(self) -> None:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_id, task_type, session_id, owner_id, payload_json, status, error, result_json,
                       created_at, started_at, completed_at, attempt_count, max_attempts
                FROM task_queue
                ORDER BY created_at ASC
                """
            ).fetchall()
        with self._lock:
            for row in rows:
                raw_status = row[5]
                attempt_count = int(row[11] or 0)
                max_attempts = int(row[12] or 1)
                should_resume = raw_status in {"queued", "running"} and attempt_count < max_attempts
                status = "queued" if should_resume else raw_status
                if raw_status in {"queued", "running"} and not should_resume:
                    status = "failed"
                record = {
                    "task_id": row[0],
                    "task_type": row[1],
                    "session_id": row[2],
                    "owner_id": row[3],
                    "payload": json.loads(row[4]),
                    "status": status,
                    "error": row[6] or ("Worker restarted before task completion." if raw_status in {"queued", "running"} else None),
                    "result": json.loads(row[7]) if row[7] else None,
                    "created_at": row[8],
                    "started_at": row[9],
                    "completed_at": None if should_resume else (row[10] or (_utc_iso() if raw_status in {"queued", "running"} else None)),
                    "attempt_count": attempt_count,
                    "max_attempts": max_attempts,
                    "runner": None,
                }
                self._tasks[record["task_id"]] = record
                self._persist_record(record)
                if should_resume:
                    self._queue.put({"task_id": record["task_id"]})

    def submit(
        self,
        *,
        task_type: str,
        session_id: str,
        owner_id: str,
        payload: dict | None = None,
        runner: Callable[[], dict] | None = None,
    ) -> dict:
        task = super().submit(
            task_type=task_type,
            session_id=session_id,
            owner_id=owner_id,
            payload=payload,
            runner=runner,
        )
        with self._lock:
            self._persist_record(self._tasks[task["task_id"]])
        return task

    def snapshot(self) -> dict:
        payload = super().snapshot()
        payload["backend"] = "sqlite"
        payload["sqlite_path"] = self.path.as_posix()
        return payload

    def _execute(self, record: dict) -> dict:
        result = super()._execute(record)
        with self._lock:
            self._persist_record(record)
        return result

    def _emit(self, record: dict) -> None:
        with self._lock:
            source = self._tasks.get(record["task_id"])
            if source is not None:
                self._persist_record(source)
        super()._emit(record)

    def _persist_record(self, record: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO task_queue (
                    task_id, task_type, session_id, owner_id, payload_json, status, error, result_json,
                    created_at, started_at, completed_at, attempt_count, max_attempts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    task_type = excluded.task_type,
                    session_id = excluded.session_id,
                    owner_id = excluded.owner_id,
                    payload_json = excluded.payload_json,
                    status = excluded.status,
                    error = excluded.error,
                    result_json = excluded.result_json,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    attempt_count = excluded.attempt_count,
                    max_attempts = excluded.max_attempts
                """,
                (
                    record["task_id"],
                    record["task_type"],
                    record["session_id"],
                    record["owner_id"],
                    json.dumps(record["payload"], ensure_ascii=False),
                    record["status"],
                    record["error"],
                    json.dumps(record["result"], ensure_ascii=False) if record["result"] is not None else None,
                    record["created_at"],
                    record["started_at"],
                    record["completed_at"],
                    record["attempt_count"],
                    record["max_attempts"],
                ),
            )


class PostgresTaskQueue(InMemoryTaskQueue):
    placeholder = "%s"

    def __init__(
        self,
        dsn: str,
        worker_threads: int = 1,
        max_queue_size: int = 100,
        max_attempts: int = 1,
        on_update: Callable[[dict], None] | None = None,
        handlers: dict[str, TaskHandler] | None = None,
        connect_factory: Callable[[str], object] | None = None,
    ) -> None:
        self.dsn = dsn
        self.connect_factory = connect_factory or self._default_connect_factory()
        super().__init__(
            worker_threads=worker_threads,
            max_queue_size=max_queue_size,
            max_attempts=max_attempts,
            on_update=on_update,
            handlers=handlers,
        )
        self._initialize()
        self._load_existing_tasks()

    def _default_connect_factory(self) -> Callable[[str], object]:
        try:
            psycopg = importlib.import_module("psycopg")
            return psycopg.connect
        except ImportError:
            psycopg2 = importlib.import_module("psycopg2")
            return psycopg2.connect

    @contextmanager
    def _connect(self):
        connection = self.connect_factory(self.dsn)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _query(self, sql: str) -> str:
        return sql.replace("?", self.placeholder)

    def _initialize(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS task_queue (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_queue_status_created_at ON task_queue(status, created_at)"
            )
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'task_queue'
                """
            )
            columns = {str(row[0]) for row in cursor.fetchall()}
            if "attempt_count" not in columns:
                cursor.execute("ALTER TABLE task_queue ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
            if "max_attempts" not in columns:
                cursor.execute("ALTER TABLE task_queue ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 1")
            cursor.close()

    def _load_existing_tasks(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT task_id, task_type, session_id, owner_id, payload_json, status, error, result_json,
                       created_at, started_at, completed_at, attempt_count, max_attempts
                FROM task_queue
                ORDER BY created_at ASC
                """
            )
            rows = cursor.fetchall()
            cursor.close()
        with self._lock:
            for row in rows:
                raw_status = row[5]
                attempt_count = int(row[11] or 0)
                max_attempts = int(row[12] or 1)
                should_resume = raw_status in {"queued", "running"} and attempt_count < max_attempts
                status = "queued" if should_resume else raw_status
                if raw_status in {"queued", "running"} and not should_resume:
                    status = "failed"
                record = {
                    "task_id": row[0],
                    "task_type": row[1],
                    "session_id": row[2],
                    "owner_id": row[3],
                    "payload": json.loads(row[4]),
                    "status": status,
                    "error": row[6] or ("Worker restarted before task completion." if raw_status in {"queued", "running"} else None),
                    "result": json.loads(row[7]) if row[7] else None,
                    "created_at": row[8],
                    "started_at": row[9],
                    "completed_at": None if should_resume else (row[10] or (_utc_iso() if raw_status in {"queued", "running"} else None)),
                    "attempt_count": attempt_count,
                    "max_attempts": max_attempts,
                    "runner": None,
                }
                self._tasks[record["task_id"]] = record
                self._persist_record(record)
                if should_resume:
                    self._queue.put({"task_id": record["task_id"]})

    def submit(
        self,
        *,
        task_type: str,
        session_id: str,
        owner_id: str,
        payload: dict | None = None,
        runner: Callable[[], dict] | None = None,
    ) -> dict:
        task = super().submit(
            task_type=task_type,
            session_id=session_id,
            owner_id=owner_id,
            payload=payload,
            runner=runner,
        )
        with self._lock:
            self._persist_record(self._tasks[task["task_id"]])
        return task

    def snapshot(self) -> dict:
        payload = super().snapshot()
        payload["backend"] = "postgres"
        payload["postgres_dsn_configured"] = bool(self.dsn)
        return payload

    def _execute(self, record: dict) -> dict:
        result = super()._execute(record)
        with self._lock:
            self._persist_record(record)
        return result

    def _emit(self, record: dict) -> None:
        with self._lock:
            source = self._tasks.get(record["task_id"])
            if source is not None:
                self._persist_record(source)
        super()._emit(record)

    def _persist_record(self, record: dict) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                self._query(
                    """
                    INSERT INTO task_queue (
                        task_id, task_type, session_id, owner_id, payload_json, status, error, result_json,
                        created_at, started_at, completed_at, attempt_count, max_attempts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        task_type = excluded.task_type,
                        session_id = excluded.session_id,
                        owner_id = excluded.owner_id,
                        payload_json = excluded.payload_json,
                        status = excluded.status,
                        error = excluded.error,
                        result_json = excluded.result_json,
                        started_at = excluded.started_at,
                        completed_at = excluded.completed_at,
                        attempt_count = excluded.attempt_count,
                        max_attempts = excluded.max_attempts
                    """
                ),
                (
                    record["task_id"],
                    record["task_type"],
                    record["session_id"],
                    record["owner_id"],
                    json.dumps(record["payload"], ensure_ascii=False),
                    record["status"],
                    record["error"],
                    json.dumps(record["result"], ensure_ascii=False) if record["result"] is not None else None,
                    record["created_at"],
                    record["started_at"],
                    record["completed_at"],
                    record["attempt_count"],
                    record["max_attempts"],
                ),
            )
            cursor.close()


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()
