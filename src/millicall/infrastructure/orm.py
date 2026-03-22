from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text

metadata = MetaData()

extensions_table = Table(
    "extensions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("number", String(20), unique=True, nullable=False),
    Column("display_name", String(100), nullable=False),
    Column("enabled", Boolean, default=True, nullable=False),
    Column("peer_id", Integer, ForeignKey("peers.id", ondelete="SET NULL"), nullable=True),
)

peers_table = Table(
    "peers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(50), unique=True, nullable=False),
    Column("password", String(100), nullable=False),
    Column("transport", String(10), default="udp", nullable=False),
    Column("codecs", Text, default="ulaw,alaw", nullable=False),  # comma-separated
    Column("ip_address", String(45), nullable=True),
    Column("extension_id", Integer, ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True),
)

devices_table = Table(
    "devices",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("mac_address", String(17), unique=True, nullable=False),  # AA:BB:CC:DD:EE:FF
    Column("ip_address", String(45), nullable=True),
    Column("hostname", String(100), nullable=True),
    Column("model", String(50), nullable=True),
    Column("peer_id", Integer, ForeignKey("peers.id", ondelete="SET NULL"), nullable=True),
    Column("extension_id", Integer, ForeignKey("extensions.id", ondelete="SET NULL"), nullable=True),
    Column("provisioned", Boolean, default=False, nullable=False),
    Column("last_seen", DateTime, nullable=True),
)
