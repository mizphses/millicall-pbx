"""Initial schema - extensions and peers tables

Revision ID: 001_initial
Revises:
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extensions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("number", sa.String(20), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("peer_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "peers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("password", sa.String(100), nullable=False),
        sa.Column("transport", sa.String(10), default="udp", nullable=False),
        sa.Column("codecs", sa.Text(), default="ulaw,alaw", nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("extension_id", sa.Integer(), nullable=True),
    )

    # Add foreign keys after both tables exist
    with op.batch_alter_table("extensions") as batch_op:
        batch_op.create_foreign_key(
            "fk_extensions_peer_id",
            "peers",
            ["peer_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("peers") as batch_op:
        batch_op.create_foreign_key(
            "fk_peers_extension_id",
            "extensions",
            ["extension_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_table("peers")
    op.drop_table("extensions")
