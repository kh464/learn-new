from app.task_queue import PostgresTaskQueue


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = []

    def execute(self, query, params=None):
        text = " ".join(str(query).split())
        self.connection.executed.append((text, params))
        if "SELECT column_name FROM information_schema.columns" in text:
            self.result = [(column,) for column in self.connection.columns]
        elif "CREATE TABLE IF NOT EXISTS task_queue" in text:
            self.result = []
        elif "CREATE INDEX IF NOT EXISTS idx_task_queue_status_created_at" in text:
            self.result = []
        elif "ALTER TABLE task_queue ADD COLUMN" in text:
            self.result = []
        elif "SELECT task_id, task_type, session_id, owner_id, payload_json, status, error, result_json," in text:
            rows = self.connection.tasks.values()
            if "WHERE task_id =" in text:
                task = self.connection.tasks.get(params[0])
                rows = [task] if task is not None else []
            self.result = [
                (
                    task["task_id"],
                    task["task_type"],
                    task["session_id"],
                    task["owner_id"],
                    task["payload_json"],
                    task["status"],
                    task["error"],
                    task["result_json"],
                    task["created_at"],
                    task["started_at"],
                    task["completed_at"],
                    task["attempt_count"],
                    task["max_attempts"],
                    task.get("lease_owner"),
                    task.get("lease_expires_at"),
                )
                for task in rows
            ]
        elif "UPDATE task_queue SET status = 'running'" in text and "RETURNING" in text:
            lease_owner = params[0]
            lease_expires_at = params[1]
            started_at = params[2]
            for task in self.connection.tasks.values():
                lease_expired = not task.get("lease_expires_at") or task["lease_expires_at"] <= self.connection.now
                claimable = task["status"] == "queued" or (
                    task["status"] == "running" and lease_expired and task["attempt_count"] < task["max_attempts"]
                )
                if claimable:
                    task["status"] = "running"
                    task["lease_owner"] = lease_owner
                    task["lease_expires_at"] = lease_expires_at
                    task["started_at"] = started_at
                    task["attempt_count"] += 1
                    self.result = [
                        (
                            task["task_id"],
                            task["task_type"],
                            task["session_id"],
                            task["owner_id"],
                            task["payload_json"],
                            task["status"],
                            task["error"],
                            task["result_json"],
                            task["created_at"],
                            task["started_at"],
                            task["completed_at"],
                            task["attempt_count"],
                            task["max_attempts"],
                            task.get("lease_owner"),
                            task.get("lease_expires_at"),
                        )
                    ]
                    return
            self.result = []
        elif "INSERT INTO task_queue" in text:
            task_id = params[0]
            self.connection.tasks[task_id] = {
                "task_id": params[0],
                "task_type": params[1],
                "session_id": params[2],
                "owner_id": params[3],
                "payload_json": params[4],
                "status": params[5],
                "error": params[6],
                "result_json": params[7],
                "created_at": params[8],
                "started_at": params[9],
                "completed_at": params[10],
                "attempt_count": params[11],
                "max_attempts": params[12],
                "lease_owner": params[13],
                "lease_expires_at": params[14],
            }
            self.result = []
        else:
            self.result = []

    def fetchall(self):
        return list(self.result)

    def fetchone(self):
        return self.result[0] if self.result else None

    def close(self):
        return None


class FakeConnection:
    def __init__(self):
        self.executed = []
        self.now = "2026-04-07T00:00:00+00:00"
        self.columns = {
            "task_id",
            "task_type",
            "session_id",
            "owner_id",
            "payload_json",
            "status",
            "error",
            "result_json",
            "created_at",
            "started_at",
            "completed_at",
            "attempt_count",
            "max_attempts",
            "lease_owner",
            "lease_expires_at",
        }
        self.tasks = {}

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        return None

    def close(self):
        return None


def test_postgres_task_queue_persists_completed_tasks() -> None:
    connection = FakeConnection()
    queue = PostgresTaskQueue(
        dsn="postgresql://example",
        connect_factory=lambda _dsn: connection,
        worker_threads=1,
        max_queue_size=8,
        handlers={"turn": lambda payload: {"session_id": payload["session_id"], "status": "ok"}},
    )
    task = queue.submit(
        task_type="turn",
        session_id="session-1",
        owner_id="alice",
        payload={"session_id": "session-1"},
    )

    completed = queue.wait(task["task_id"], timeout_seconds=5)
    queue.shutdown()

    reloaded = PostgresTaskQueue(
        dsn="postgresql://example",
        connect_factory=lambda _dsn: connection,
        worker_threads=1,
        max_queue_size=8,
    )
    restored = reloaded.get(task["task_id"])
    reloaded.shutdown()

    assert completed["status"] == "completed"
    assert restored["result"]["session_id"] == "session-1"


def test_postgres_task_queue_retries_failed_tasks_until_success() -> None:
    connection = FakeConnection()
    attempts = {"count": 0}

    def handler(payload: dict) -> dict:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("temporary")
        return {"session_id": payload["session_id"], "status": "ok"}

    queue = PostgresTaskQueue(
        dsn="postgresql://example",
        connect_factory=lambda _dsn: connection,
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


def test_postgres_task_queue_reclaims_expired_lease_and_completes_task() -> None:
    connection = FakeConnection()
    connection.tasks["task-1"] = {
        "task_id": "task-1",
        "task_type": "turn",
        "session_id": "session-1",
        "owner_id": "alice",
        "payload_json": '{"session_id": "session-1"}',
        "status": "running",
        "error": None,
        "result_json": None,
        "created_at": "2026-04-07T00:00:00+00:00",
        "started_at": "2026-04-07T00:00:01+00:00",
        "completed_at": None,
        "attempt_count": 0,
        "max_attempts": 2,
        "lease_owner": "worker-old",
        "lease_expires_at": "2026-04-06T23:59:00+00:00",
    }

    queue = PostgresTaskQueue(
        dsn="postgresql://example",
        connect_factory=lambda _dsn: connection,
        worker_threads=1,
        max_queue_size=8,
        handlers={"turn": lambda payload: {"session_id": payload["session_id"], "status": "ok"}},
    )
    queue.start()

    completed = queue.wait("task-1", timeout_seconds=5)
    queue.shutdown()

    assert completed["status"] == "completed"
    assert completed["attempt_count"] == 1
