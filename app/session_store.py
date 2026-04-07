from __future__ import annotations

import importlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterator, Protocol

from app.models import LearnerState


class SessionStore(Protocol):
    def save_state(self, state: LearnerState) -> None:
        ...

    def load_state(self, session_id: str) -> LearnerState:
        ...

    def list_session_ids(self) -> list[str]:
        ...

    def write_checkpoint(self, state: LearnerState) -> str:
        ...

    def list_checkpoints(self, session_id: str) -> list[dict]:
        ...

    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> LearnerState:
        ...


class SqlSessionStore:
    placeholder = "?"

    def __init__(self) -> None:
        self._initialize()

    @contextmanager
    def _connect(self):
        raise NotImplementedError

    def _query(self, sql: str) -> str:
        return sql.replace("?", self.placeholder)

    def _initialize(self) -> None:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    current_stage INTEGER NOT NULL,
                    teaching_mode TEXT NOT NULL,
                    assessment_score REAL NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    current_stage INTEGER NOT NULL,
                    teaching_mode TEXT NOT NULL,
                    assessment_score REAL NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_session_created_at ON checkpoints(session_id, created_at)"
            )
            cursor.close()

    def save_state(self, state: LearnerState) -> None:
        payload = json.dumps(state.model_dump(mode="json"), ensure_ascii=False)
        updated_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                self._query(
                    """
                    INSERT INTO sessions (
                        session_id,
                        domain,
                        owner_id,
                        current_stage,
                        teaching_mode,
                        assessment_score,
                        state_json,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        domain = excluded.domain,
                        owner_id = excluded.owner_id,
                        current_stage = excluded.current_stage,
                        teaching_mode = excluded.teaching_mode,
                        assessment_score = excluded.assessment_score,
                        state_json = excluded.state_json,
                        updated_at = excluded.updated_at
                    """
                ),
                (
                    state.session_id,
                    state.domain,
                    state.owner_id,
                    state.current_stage,
                    state.teaching_mode,
                    state.assessment_score,
                    payload,
                    updated_at,
                ),
            )
            cursor.close()

    def load_state(self, session_id: str) -> LearnerState:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(self._query("SELECT state_json FROM sessions WHERE session_id = ?"), (session_id,))
            row = cursor.fetchone()
            cursor.close()
        if row is None:
            raise FileNotFoundError(session_id)
        return LearnerState.model_validate_json(row[0])

    def list_session_ids(self) -> list[str]:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT session_id FROM sessions ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            cursor.close()
        return [str(row[0]) for row in rows]

    def write_checkpoint(self, state: LearnerState) -> str:
        created_at = datetime.now(UTC).isoformat()
        checkpoint_id = f"stage-{state.current_stage}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
        payload = json.dumps(state.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                self._query(
                    """
                    INSERT INTO checkpoints (
                        checkpoint_id,
                        session_id,
                        current_stage,
                        teaching_mode,
                        assessment_score,
                        state_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                ),
                (
                    checkpoint_id,
                    state.session_id,
                    state.current_stage,
                    state.teaching_mode,
                    state.assessment_score,
                    payload,
                    created_at,
                ),
            )
            cursor.close()
        return checkpoint_id

    def list_checkpoints(self, session_id: str) -> list[dict]:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                self._query(
                    """
                    SELECT checkpoint_id, created_at, current_stage, teaching_mode, assessment_score
                    FROM checkpoints
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                    """
                ),
                (session_id,),
            )
            rows = cursor.fetchall()
            cursor.close()
        return [
            {
                "checkpoint_id": str(row[0]),
                "created_at": str(row[1]),
                "current_stage": int(row[2]),
                "teaching_mode": str(row[3]),
                "assessment_score": float(row[4]),
            }
            for row in rows
        ]

    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> LearnerState:
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                self._query(
                    """
                    SELECT state_json
                    FROM checkpoints
                    WHERE session_id = ? AND checkpoint_id = ?
                    """
                ),
                (session_id, checkpoint_id),
            )
            row = cursor.fetchone()
            cursor.close()
        if row is None:
            raise FileNotFoundError(checkpoint_id)
        return LearnerState.model_validate_json(row[0])


class SQLiteSessionStore(SqlSessionStore):
    placeholder = "?"

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


class PostgresSessionStore(SqlSessionStore):
    placeholder = "%s"

    def __init__(self, dsn: str, connect_factory: Callable[[str], object] | None = None) -> None:
        self.dsn = dsn
        self.connect_factory = connect_factory or self._default_connect_factory()
        super().__init__()

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
