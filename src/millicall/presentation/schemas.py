from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Auth ---


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    is_admin: bool = False


class UserUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    is_admin: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4, max_length=100)


# --- Extensions ---


class ExtensionCreate(BaseModel):
    number: str = Field(..., min_length=1, max_length=20, pattern=r"^\d+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    peer_id: int | None = None
    type: str = "phone"
    ai_agent_id: int | None = None


class ExtensionUpdate(BaseModel):
    number: str = Field(..., min_length=1, max_length=20, pattern=r"^\d+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    peer_id: int | None = None
    type: str = "phone"
    ai_agent_id: int | None = None


class ExtensionResponse(BaseModel):
    id: int
    number: str
    display_name: str
    enabled: bool
    peer_id: int | None
    type: str = "phone"
    ai_agent_id: int | None = None


# --- Peers ---


class PeerCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=4, max_length=100)
    transport: str = Field(default="udp", pattern=r"^(udp|tcp)$")
    codecs: list[str] = Field(default=["ulaw", "alaw"])
    ip_address: str | None = None
    extension_id: int | None = None


class PeerUpdate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=4, max_length=100)
    transport: str = Field(default="udp", pattern=r"^(udp|tcp)$")
    codecs: list[str] = Field(default=["ulaw", "alaw"])
    ip_address: str | None = None
    extension_id: int | None = None


class PeerResponse(BaseModel):
    id: int
    username: str
    password: str
    transport: str
    codecs: list[str]
    ip_address: str | None
    extension_id: int | None


# --- Trunks ---


class TrunkCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)
    did_number: str = ""
    caller_id: str = ""
    incoming_dest: str = ""
    outbound_prefixes: str = ""
    enabled: bool = True


class TrunkUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)
    did_number: str = ""
    caller_id: str = ""
    incoming_dest: str = ""
    outbound_prefixes: str = ""
    enabled: bool = True


class TrunkResponse(BaseModel):
    id: int
    name: str
    display_name: str
    host: str
    username: str
    password: str
    did_number: str
    caller_id: str
    incoming_dest: str
    outbound_prefixes: str
    enabled: bool


# --- AI Agents ---


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    extension_number: str = Field(..., min_length=1, max_length=20)
    system_prompt: str = Field(..., min_length=1)
    greeting_text: str = "お電話ありがとうございます。ご用件をどうぞ。"
    coefont_voice_id: str = ""
    tts_provider: str = "coefont"
    google_tts_voice: str = "ja-JP-Chirp3-HD-Aoede"
    llm_provider: str = "google"
    llm_model: str = "gemini-2.5-flash"
    max_history: int = 10
    enabled: bool = True


class AgentUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    extension_number: str = Field(..., min_length=1, max_length=20)
    system_prompt: str = Field(..., min_length=1)
    greeting_text: str = "お電話ありがとうございます。ご用件をどうぞ。"
    coefont_voice_id: str = ""
    tts_provider: str = "coefont"
    google_tts_voice: str = "ja-JP-Chirp3-HD-Aoede"
    llm_provider: str = "google"
    llm_model: str = "gemini-2.5-flash"
    max_history: int = 10
    enabled: bool = True


class AgentResponse(BaseModel):
    id: int
    name: str
    extension_number: str
    system_prompt: str
    greeting_text: str
    coefont_voice_id: str
    tts_provider: str
    google_tts_voice: str
    llm_provider: str
    llm_model: str
    max_history: int
    enabled: bool


# --- Settings ---


class SettingItem(BaseModel):
    key: str
    value: str
    description: str | None = None


# --- CDR ---


class CDRResponse(BaseModel):
    id: int
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


# --- Call History ---


class CallLogResponse(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    extension_number: str
    caller_channel: str
    started_at: datetime | None
    ended_at: datetime | None
    turn_count: int


class CallMessageResponse(BaseModel):
    id: int
    call_log_id: int
    role: str
    content: str
    turn: int
    created_at: datetime | None


class CallLogDetailResponse(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    extension_number: str
    caller_channel: str
    started_at: datetime | None
    ended_at: datetime | None
    turn_count: int
    messages: list[CallMessageResponse]


# --- Contacts ---


class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=1, max_length=30)
    company: str = Field(default="", max_length=100)
    department: str = Field(default="", max_length=100)
    notes: str = ""


class ContactUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=1, max_length=30)
    company: str = Field(default="", max_length=100)
    department: str = Field(default="", max_length=100)
    notes: str = ""


class ContactResponse(BaseModel):
    id: int
    name: str
    phone_number: str
    company: str
    department: str
    notes: str


# --- Workflows ---


class NodePosition(BaseModel):
    x: float
    y: float


class WorkflowNode(BaseModel):
    id: str
    type: str
    position: NodePosition
    label: str = ""
    config: dict[str, Any] = {}
    data: dict[str, Any] = {}


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str | None = Field(None, alias="sourceHandle")
    target_handle: str | None = Field(None, alias="targetHandle")
    label: str | None = None


class WorkflowDefinition(BaseModel):
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []


class TTSConfig(BaseModel):
    tts_provider: str = "google"
    google_tts_voice: str = "ja-JP-Chirp3-HD-Aoede"
    coefont_voice_id: str = ""


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    number: str = Field(..., min_length=1, max_length=20, pattern=r"^\d+$")
    description: str = ""
    workflow_type: str = Field(..., pattern=r"^(ivr|ai_workflow)$")
    definition: WorkflowDefinition = WorkflowDefinition()
    default_tts_config: TTSConfig = TTSConfig()
    enabled: bool = True


class WorkflowUpdate(BaseModel):
    name: str | None = None
    number: str | None = None
    description: str | None = None
    workflow_type: str | None = None
    definition: WorkflowDefinition | None = None
    default_tts_config: TTSConfig | None = None
    enabled: bool | None = None


class WorkflowResponse(BaseModel):
    id: int
    name: str
    number: str
    description: str
    extension_id: int | None
    workflow_type: str
    definition: WorkflowDefinition
    default_tts_config: TTSConfig
    enabled: bool
    created_at: datetime | None
    updated_at: datetime | None


class WorkflowListResponse(BaseModel):
    id: int
    name: str
    number: str
    description: str
    extension_id: int | None
    workflow_type: str
    enabled: bool
    node_count: int
    created_at: datetime | None
    updated_at: datetime | None
