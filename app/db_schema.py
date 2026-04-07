from __future__ import annotations

from sqlalchemy import Column, Float, Index, Integer, MetaData, Table, Text


metadata = MetaData()

sessions = Table(
    "sessions",
    metadata,
    Column("session_id", Text, primary_key=True),
    Column("domain", Text, nullable=False),
    Column("owner_id", Text, nullable=False),
    Column("current_stage", Integer, nullable=False),
    Column("teaching_mode", Text, nullable=False),
    Column("assessment_score", Float, nullable=False),
    Column("state_json", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

checkpoints = Table(
    "checkpoints",
    metadata,
    Column("checkpoint_id", Text, primary_key=True),
    Column("session_id", Text, nullable=False),
    Column("current_stage", Integer, nullable=False),
    Column("teaching_mode", Text, nullable=False),
    Column("assessment_score", Float, nullable=False),
    Column("state_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)

Index("idx_checkpoints_session_created_at", checkpoints.c.session_id, checkpoints.c.created_at)
