"""add task queue leases

Revision ID: 20260407_000003
Revises: 20260407_000002
Create Date: 2026-04-07 23:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_000003"
down_revision = "20260407_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("task_queue", sa.Column("lease_owner", sa.Text(), nullable=True))
    op.add_column("task_queue", sa.Column("lease_expires_at", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("task_queue", "lease_expires_at")
    op.drop_column("task_queue", "lease_owner")
