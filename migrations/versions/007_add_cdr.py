"""Add CDR table for call detail records

Revision ID: 007_add_cdr
Revises: 006_unify_extensions
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_add_cdr"
down_revision: Union[str, None] = "006_unify_extensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cdr",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uniqueid", sa.String(150), unique=True, nullable=False),
        sa.Column("call_date", sa.DateTime(), nullable=False),
        sa.Column("clid", sa.String(200), nullable=False, server_default=""),
        sa.Column("src", sa.String(80), nullable=False),
        sa.Column("dst", sa.String(80), nullable=False),
        sa.Column("dcontext", sa.String(80), nullable=False),
        sa.Column("channel", sa.String(200), nullable=False),
        sa.Column("dst_channel", sa.String(200), nullable=False, server_default=""),
        sa.Column("duration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billsec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disposition", sa.String(30), nullable=False),
        sa.Column("account_code", sa.String(50), nullable=False, server_default=""),
        sa.Column("userfield", sa.String(255), nullable=False, server_default=""),
    )
    op.create_index("ix_cdr_call_date", "cdr", ["call_date"])


def downgrade() -> None:
    op.drop_index("ix_cdr_call_date", table_name="cdr")
    op.drop_table("cdr")
