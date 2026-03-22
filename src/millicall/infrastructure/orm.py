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
    Column("type", String(20), default="phone", nullable=False),
    Column("ai_agent_id", Integer, ForeignKey("ai_agents.id", ondelete="SET NULL"), nullable=True),
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

trunks_table = Table(
    "trunks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(50), unique=True, nullable=False),
    Column("display_name", String(100), nullable=False),
    Column("host", String(100), nullable=False),
    Column("username", String(50), nullable=False),
    Column("password", String(100), nullable=False),
    Column("did_number", String(30), nullable=False, server_default=""),
    Column("caller_id", String(30), nullable=False, server_default=""),
    Column("incoming_dest", String(20), nullable=False, server_default=""),
    Column("outbound_prefixes", String(200), nullable=False, server_default=""),
    Column("enabled", Boolean, default=True, nullable=False),
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

call_logs_table = Table(
    "call_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("agent_id", Integer, nullable=False),
    Column("agent_name", String(100), nullable=False),
    Column("extension_number", String(20), nullable=False),
    Column("caller_channel", String(200), nullable=False),
    Column("started_at", DateTime, nullable=False),
    Column("ended_at", DateTime, nullable=True),
    Column("turn_count", Integer, nullable=False, default=0),
)

call_messages_table = Table(
    "call_messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("call_log_id", Integer, ForeignKey("call_logs.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(20), nullable=False),  # "user" or "assistant"
    Column("content", Text, nullable=False),
    Column("turn", Integer, nullable=False, default=0),
    Column("created_at", DateTime, nullable=False),
)

cdr_table = Table(
    "cdr",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uniqueid", String(150), unique=True, nullable=False),
    Column("call_date", DateTime, nullable=False),
    Column("clid", String(200), nullable=False, server_default=""),
    Column("src", String(80), nullable=False),
    Column("dst", String(80), nullable=False),
    Column("dcontext", String(80), nullable=False),
    Column("channel", String(200), nullable=False),
    Column("dst_channel", String(200), nullable=False, server_default=""),
    Column("duration", Integer, nullable=False, server_default="0"),
    Column("billsec", Integer, nullable=False, server_default="0"),
    Column("disposition", String(30), nullable=False),
    Column("account_code", String(50), nullable=False, server_default=""),
    Column("userfield", String(255), nullable=False, server_default=""),
)

settings_table = Table(
    "app_settings",
    metadata,
    Column("key", String(100), primary_key=True),
    Column("value", Text, nullable=False, default=""),
    Column("description", String(200), nullable=True),
)
