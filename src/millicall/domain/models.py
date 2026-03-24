from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Extension:
    number: str
    display_name: str
    enabled: bool = True
    peer_id: int | None = None
    type: str = "phone"  # "phone" or "ai_agent"
    ai_agent_id: int | None = None
    id: int | None = None


@dataclass
class Peer:
    username: str
    password: str
    transport: str = "udp"
    codecs: list[str] = field(default_factory=lambda: ["ulaw", "alaw"])
    ip_address: str | None = None
    extension_id: int | None = None
    id: int | None = None


@dataclass
class PeerWithExtension:
    """Peer with its associated extension info for config generation."""

    peer: Peer
    extension: Extension | None = None


@dataclass
class Trunk:
    name: str  # slug for Asterisk section names, e.g. "hikari-trunk"
    display_name: str
    host: str
    username: str
    password: str
    did_number: str = ""
    caller_id: str = ""
    incoming_dest: str = ""
    outbound_prefixes: str = ""  # comma-separated, e.g. "186,184,0086"
    enabled: bool = True
    id: int | None = None


@dataclass
class Device:
    mac_address: str
    ip_address: str | None = None
    hostname: str | None = None
    model: str | None = None
    peer_id: int | None = None
    extension_id: int | None = None
    provisioned: bool = False
    last_seen: datetime | None = None
    active: bool = True
    id: int | None = None


@dataclass
class AIAgent:
    name: str
    extension_number: str
    system_prompt: str
    coefont_voice_id: str
    greeting_text: str = "お電話ありがとうございます。ご用件をどうぞ。"
    tts_provider: str = "coefont"  # coefont or google
    google_tts_voice: str = "ja-JP-Chirp3-HD-Aoede"
    llm_provider: str = "google"
    llm_model: str = "gemini-2.5-flash"
    max_history: int = 10
    enabled: bool = True
    id: int | None = None


@dataclass
class CallLog:
    agent_id: int
    agent_name: str
    extension_number: str
    caller_channel: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    turn_count: int = 0
    id: int | None = None


@dataclass
class CDR:
    uniqueid: str
    call_date: datetime
    src: str
    dst: str
    dcontext: str
    channel: str
    dst_channel: str
    duration: int
    billsec: int
    disposition: str
    clid: str = ""
    account_code: str = ""
    userfield: str = ""
    id: int | None = None


@dataclass
class User:
    username: str
    hashed_password: str
    display_name: str
    is_admin: bool = True
    role: str = "admin"  # "admin", "user", "mcp"
    id: int | None = None


@dataclass
class CallMessage:
    call_log_id: int
    role: str  # "user" or "assistant"
    content: str
    turn: int = 0
    created_at: datetime | None = None
    id: int | None = None


@dataclass
class Contact:
    name: str
    phone_number: str
    company: str = ""
    department: str = ""
    notes: str = ""
    id: int | None = None


@dataclass
class Workflow:
    name: str
    number: str  # extension number to dial this workflow
    workflow_type: str  # "workflow"
    definition: dict = field(default_factory=dict)
    default_tts_config: dict = field(default_factory=dict)  # workflow-level TTS defaults
    extension_id: int | None = None  # auto-managed
    description: str = ""
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
