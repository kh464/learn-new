from pathlib import Path

from app.models import LearnerProfile, LearnerState
from app.session_store import PostgresSessionStore


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = []

    def execute(self, query, params=None):
        text = " ".join(str(query).split())
        self.connection.executed.append((text, params))
        if "INSERT INTO sessions" in text:
            session_id = params[0]
            self.connection.sessions[session_id] = {
                "session_id": params[0],
                "domain": params[1],
                "owner_id": params[2],
                "current_stage": params[3],
                "teaching_mode": params[4],
                "assessment_score": params[5],
                "state_json": params[6],
                "updated_at": params[7],
            }
            self.result = []
        elif "SELECT state_json FROM sessions" in text:
            row = self.connection.sessions.get(params[0])
            self.result = [(row["state_json"],)] if row else []
        elif "SELECT session_id FROM sessions" in text:
            ordered = sorted(self.connection.sessions.values(), key=lambda item: item["updated_at"], reverse=True)
            self.result = [(item["session_id"],) for item in ordered]
        elif "INSERT INTO checkpoints" in text:
            checkpoint_id = params[0]
            self.connection.checkpoints[checkpoint_id] = {
                "checkpoint_id": params[0],
                "session_id": params[1],
                "current_stage": params[2],
                "teaching_mode": params[3],
                "assessment_score": params[4],
                "state_json": params[5],
                "created_at": params[6],
            }
            self.result = []
        elif "SELECT checkpoint_id, created_at, current_stage, teaching_mode, assessment_score" in text:
            rows = [
                item for item in self.connection.checkpoints.values() if item["session_id"] == params[0]
            ]
            rows.sort(key=lambda item: item["created_at"])
            self.result = [
                (
                    item["checkpoint_id"],
                    item["created_at"],
                    item["current_stage"],
                    item["teaching_mode"],
                    item["assessment_score"],
                )
                for item in rows
            ]
        elif "SELECT state_json FROM checkpoints" in text:
            row = self.connection.checkpoints.get(params[1])
            self.result = [(row["state_json"],)] if row and row["session_id"] == params[0] else []
        else:
            self.result = []

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return list(self.result)

    def close(self):
        return None


class FakeConnection:
    def __init__(self):
        self.executed = []
        self.sessions = {}
        self.checkpoints = {}

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        return None

    def close(self):
        return None


def test_postgres_session_store_round_trips_state_and_checkpoints(tmp_path: Path) -> None:
    connection = FakeConnection()
    store = PostgresSessionStore(
        dsn="postgresql://example",
        connect_factory=lambda dsn: connection,
    )
    state = LearnerState.new(
        domain="Python async programming",
        profile=LearnerProfile(goal="Master async/await"),
        owner_id="alice",
    )

    store.save_state(state)
    checkpoint_id = store.write_checkpoint(state)

    loaded = store.load_state(state.session_id)
    checkpoints = store.list_checkpoints(state.session_id)
    restored = store.load_checkpoint(state.session_id, checkpoint_id)

    assert loaded.session_id == state.session_id
    assert loaded.owner_id == "alice"
    assert checkpoints[0]["checkpoint_id"] == checkpoint_id
    assert restored.session_id == state.session_id
    assert store.list_session_ids() == [state.session_id]
