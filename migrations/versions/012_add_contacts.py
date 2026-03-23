"""Add contacts table

Revision ID: 012_add_contacts
Revises: 011_workflow_default_tts
Create Date: 2026-03-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_add_contacts"
down_revision: Union[str, None] = "011_workflow_default_tts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone_number", sa.String(30), nullable=False),
        sa.Column("company", sa.String(100), nullable=False, server_default=""),
        sa.Column("department", sa.String(100), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("contacts")
