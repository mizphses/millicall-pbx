"""Add ai_agents table

Revision ID: 003_add_ai_agents
Revises: 002_add_devices
Create Date: 2026-03-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_ai_agents"
down_revision: Union[str, None] = "002_add_devices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_agents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("extension_number", sa.String(20), unique=True, nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("greeting_text", sa.String(500), nullable=False,
                  server_default="お電話ありがとうございます。ご用件をどうぞ。"),
        sa.Column("coefont_voice_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("tts_provider", sa.String(20), nullable=False, server_default="coefont"),
        sa.Column("google_tts_voice", sa.String(100), nullable=False, server_default="ja-JP-Chirp3-HD-Aoede"),
        sa.Column("llm_provider", sa.String(20), nullable=False, server_default="google"),
        sa.Column("llm_model", sa.String(50), nullable=False, server_default="gemini-2.0-flash-lite"),
        sa.Column("max_history", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )


def downgrade() -> None:
    op.drop_table("ai_agents")
