"""create task queue table

Revision ID: 20260407_000002
Revises: 20260407_000001
Create Date: 2026-04-07 22:40:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_000002"
down_revision = "20260407_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_queue",
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index(
        "idx_task_queue_status_created_at",
        "task_queue",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_task_queue_status_created_at", table_name="task_queue")
    op.drop_table("task_queue")
