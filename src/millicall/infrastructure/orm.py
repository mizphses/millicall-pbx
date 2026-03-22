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

ai_agents_table = Table(
    "ai_agents",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False),
    Column("extension_number", String(20), unique=True, nullable=False),
    Column("system_prompt", Text, nullable=False),
    Column("greeting_text", String(500), nullable=False, default="お電話ありがとうございます。ご用件をどうぞ。"),
    Column("coefont_voice_id", String(100), nullable=False, default=""),
    Column("tts_provider", String(20), nullable=False, default="coefont"),  # coefont or google
    Column("google_tts_voice", String(100), nullable=False, default="ja-JP-Chirp3-HD-Aoede"),
    Column("llm_provider", String(20), nullable=False, default="google"),  # google, openai, anthropic
    Column("llm_model", String(50), nullable=False, default="gemini-2.0-flash-lite"),
    Column("max_history", Integer, nullable=False, default=10),
    Column("enabled", Boolean, default=True, nullable=False),
)

settings_table = Table(
    "app_settings",
    metadata,
    Column("key", String(100), primary_key=True),
    Column("value", Text, nullable=False, default=""),
    Column("description", String(200), nullable=True),
)
