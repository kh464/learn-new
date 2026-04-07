"""create session tables

Revision ID: 20260407_000001
Revises:
Create Date: 2026-04-07 21:30:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("current_stage", sa.Integer(), nullable=False),
        sa.Column("teaching_mode", sa.Text(), nullable=False),
        sa.Column("assessment_score", sa.Float(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_table(
        "checkpoints",
        sa.Column("checkpoint_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("current_stage", sa.Integer(), nullable=False),
        sa.Column("teaching_mode", sa.Text(), nullable=False),
        sa.Column("assessment_score", sa.Float(), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("checkpoint_id"),
    )
    op.create_index(
        "idx_checkpoints_session_created_at",
        "checkpoints",
        ["session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_checkpoints_session_created_at", table_name="checkpoints")
    op.drop_table("checkpoints")
    op.drop_table("sessions")
