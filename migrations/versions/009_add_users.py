"""Add users table

Revision ID: 009_add_users
Revises: 008_add_trunks
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_add_users"
down_revision: Union[str, None] = "008_add_trunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("users")
