"""Add app_settings table for API keys

Revision ID: 004_add_settings
Revises: 003_add_ai_agents
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_add_settings"
down_revision: Union[str, None] = "003_add_ai_agents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.String(200), nullable=True),
    )

    # Insert defaults
    op.execute(
        "INSERT INTO app_settings (key, value, description) VALUES "
        "('coefont_access_key', '', 'CoeFont API Access Key'), "
        "('coefont_access_secret', '', 'CoeFont API Access Secret'), "
        "('google_api_key', '', 'Google API Key (Gemini LLM & Chirp3 TTS)'), "
        "('openai_api_key', '', 'OpenAI API Key (Whisper STT & GPT)'), "
        "('anthropic_api_key', '', 'Anthropic API Key (Claude)')"
    )


def downgrade() -> None:
    op.drop_table("app_settings")
