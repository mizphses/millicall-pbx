"""Add active column to devices table

Revision ID: 014_add_device_active
Revises: 013_add_user_role
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014_add_device_active"
down_revision: str | None = "013_add_user_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )


def downgrade() -> None:
    op.drop_column("devices", "active")
