from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Extension:
    number: str
    display_name: str
    enabled: bool = True
    peer_id: int | None = None
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
class Device:
    mac_address: str
    ip_address: str | None = None
    hostname: str | None = None
    model: str | None = None
    peer_id: int | None = None
    extension_id: int | None = None
    provisioned: bool = False
    last_seen: datetime | None = None
    id: int | None = None
