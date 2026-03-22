"""Add trunks table, migrate single trunk from app_settings

Revision ID: 008_add_trunks
Revises: 007_add_cdr
Create Date: 2026-03-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_add_trunks"
down_revision: Union[str, None] = "007_add_cdr"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("host", sa.String(100), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password", sa.String(100), nullable=False),
        sa.Column("did_number", sa.String(30), nullable=False, server_default=""),
        sa.Column("caller_id", sa.String(30), nullable=False, server_default=""),
        sa.Column("incoming_dest", sa.String(20), nullable=False, server_default=""),
        sa.Column("outbound_prefixes", sa.String(200), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
    )

    # Migrate existing trunk settings to first trunk row
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT key, value FROM app_settings WHERE key LIKE 'trunk_%'"
    )).fetchall()
    s = {r[0]: r[1] for r in rows}
    if s.get("trunk_enabled", "N").upper() in ("Y", "YES", "TRUE", "1"):
        conn.execute(sa.text(
            "INSERT INTO trunks (name, display_name, host, username, password, "
            "did_number, caller_id, incoming_dest, outbound_prefixes, enabled) "
            "VALUES (:name, :display_name, :host, :username, :password, "
            ":did_number, :caller_id, :incoming_dest, :outbound_prefixes, 1)"
        ), {
            "name": "hikari-trunk",
            "display_name": "ひかり電話",
            "host": s.get("trunk_host", "192.168.1.1"),
            "username": s.get("trunk_username", ""),
            "password": s.get("trunk_password", ""),
            "did_number": s.get("trunk_did_number", ""),
            "caller_id": s.get("trunk_caller_id", ""),
            "incoming_dest": s.get("trunk_incoming_dest", ""),
            "outbound_prefixes": s.get("trunk_outbound_prefix", ""),
        })

    # Remove trunk_* from app_settings
    conn.execute(sa.text("DELETE FROM app_settings WHERE key LIKE 'trunk_%'"))


def downgrade() -> None:
    op.drop_table("trunks")
