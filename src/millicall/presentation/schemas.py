from pydantic import BaseModel, Field


class ExtensionCreate(BaseModel):
    number: str = Field(..., min_length=1, max_length=20, pattern=r"^\d+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    peer_id: int | None = None


class ExtensionUpdate(BaseModel):
    number: str = Field(..., min_length=1, max_length=20, pattern=r"^\d+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True
    peer_id: int | None = None


class ExtensionResponse(BaseModel):
    id: int
    number: str
    display_name: str
    enabled: bool
    peer_id: int | None


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
