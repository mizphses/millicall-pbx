"""Unify extensions: add type and ai_agent_id fields

Revision ID: 006_unify_extensions
Revises: 005_add_call_logs
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_unify_extensions"
down_revision: Union[str, None] = "005_add_call_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add type and ai_agent_id to extensions
    op.add_column(
        "extensions", sa.Column("type", sa.String(20), nullable=False, server_default="phone")
    )
    op.add_column("extensions", sa.Column("ai_agent_id", sa.Integer(), nullable=True))

    # Migrate existing AI agents: create extension records for each
    conn = op.get_bind()
    agents = conn.execute(
        sa.text("SELECT id, extension_number, name, enabled FROM ai_agents")
    ).fetchall()
    for agent in agents:
        # Check if extension already exists with this number
        existing = conn.execute(
            sa.text("SELECT id FROM extensions WHERE number = :num"), {"num": agent[1]}
        ).fetchone()
        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO extensions (number, display_name, enabled, type, ai_agent_id) "
                    "VALUES (:number, :name, :enabled, 'ai_agent', :agent_id)"
                ),
                {"number": agent[1], "name": agent[2], "enabled": agent[3], "agent_id": agent[0]},
            )


def downgrade() -> None:
    op.drop_column("extensions", "ai_agent_id")
    op.drop_column("extensions", "type")
