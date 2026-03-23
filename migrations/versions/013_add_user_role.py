"""Add role column to users table

Revision ID: 013_add_user_role
Revises: 012_add_contacts
Create Date: 2026-03-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013_add_user_role"
down_revision: str | None = "012_add_contacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="admin"))


def downgrade() -> None:
    op.drop_column("users", "role")
