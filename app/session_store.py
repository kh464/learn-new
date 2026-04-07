from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from app.models import LearnerState


class SQLiteSessionStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    current_stage INTEGER NOT NULL,
                    teaching_mode TEXT NOT NULL,
                    assessment_score REAL NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
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
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_session_created_at ON checkpoints(session_id, created_at)"
            )

    def save_state(self, state: LearnerState) -> None:
        payload = json.dumps(state.model_dump(mode="json"), ensure_ascii=False)
        updated_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id,
                    domain,
                    current_stage,
                    teaching_mode,
                    assessment_score,
                    state_json,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    domain = excluded.domain,
                    current_stage = excluded.current_stage,
                    teaching_mode = excluded.teaching_mode,
                    assessment_score = excluded.assessment_score,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state.session_id,
                    state.domain,
                    state.current_stage,
                    state.teaching_mode,
                    state.assessment_score,
                    payload,
                    updated_at,
                ),
            )

    def load_state(self, session_id: str) -> LearnerState:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(session_id)
        return LearnerState.model_validate_json(row["state_json"])

    def list_session_ids(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT session_id FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        return [str(row["session_id"]) for row in rows]

    def write_checkpoint(self, state: LearnerState) -> str:
        created_at = datetime.now(UTC).isoformat()
        checkpoint_id = f"stage-{state.current_stage}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
        payload = json.dumps(state.model_dump(mode="json"), ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
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
                """,
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
        return checkpoint_id

    def list_checkpoints(self, session_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT checkpoint_id, created_at, current_stage, teaching_mode, assessment_score
                FROM checkpoints
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "checkpoint_id": str(row["checkpoint_id"]),
                "created_at": str(row["created_at"]),
                "current_stage": int(row["current_stage"]),
                "teaching_mode": str(row["teaching_mode"]),
                "assessment_score": float(row["assessment_score"]),
            }
            for row in rows
        ]

    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> LearnerState:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT state_json
                FROM checkpoints
                WHERE session_id = ? AND checkpoint_id = ?
                """,
                (session_id, checkpoint_id),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(checkpoint_id)
        return LearnerState.model_validate_json(row["state_json"])
