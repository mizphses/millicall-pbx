"""Add default_tts_config to workflows table

Revision ID: 011_workflow_default_tts
Revises: 010_add_workflows
Create Date: 2026-03-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_workflow_default_tts"
down_revision: str | None = "010_add_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workflows", sa.Column("default_tts_config", sa.Text(), nullable=False, server_default="{}")
    )


def downgrade() -> None:
    op.drop_column("workflows", "default_tts_config")
