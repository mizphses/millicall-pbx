"""Add call_logs and call_messages tables for AI agent conversation history

Revision ID: 005_add_call_logs
Revises: 004_add_settings
Create Date: 2026-03-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_add_call_logs"
down_revision: Union[str, None] = "004_add_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("extension_number", sa.String(20), nullable=False),
        sa.Column("caller_channel", sa.String(200), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "call_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("call_log_id", sa.Integer(), sa.ForeignKey("call_logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("turn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("call_messages")
    op.drop_table("call_logs")
