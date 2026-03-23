"""Add devices table for provisioning

Revision ID: 002_add_devices
Revises: 001_initial
Create Date: 2026-03-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_devices"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mac_address", sa.String(17), unique=True, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("hostname", sa.String(100), nullable=True),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column(
            "peer_id", sa.Integer(), sa.ForeignKey("peers.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "extension_id",
            sa.Integer(),
            sa.ForeignKey("extensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provisioned", sa.Boolean(), default=False, nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("devices")
