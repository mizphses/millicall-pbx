"""WireGuard VPN status API."""

import asyncio
import logging

from fastapi import APIRouter, Depends

from millicall.domain.models import User
from millicall.presentation.auth import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/wireguard",
    tags=["wireguard"],
    dependencies=[Depends(get_current_user)],
)


async def _run(cmd: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


@router.get("")
async def wireguard_status(_admin: User = Depends(require_admin)):
    """Return WireGuard interface info and client config template."""
    # Read server public key and listen port from wg show
    try:
        wg_dump = await _run("wg show wg0 dump")
    except Exception:
        return {"active": False, "error": "WireGuard is not running"}

    if not wg_dump:
        return {"active": False, "error": "WireGuard is not running"}

    lines = wg_dump.strip().split("\n")
    # First line: interface info
    # private_key  public_key  listen_port  fwmark
    iface_parts = lines[0].split("\t")
    server_public_key = iface_parts[1] if len(iface_parts) > 1 else ""
    listen_port = iface_parts[2] if len(iface_parts) > 2 else "51820"

    # Parse peers
    peers = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) >= 8:
            peers.append({
                "public_key": parts[0],
                "endpoint": parts[2] if parts[2] != "(none)" else None,
                "allowed_ips": parts[3],
                "latest_handshake": int(parts[4]) if parts[4] != "0" else None,
                "transfer_rx": int(parts[5]),
                "transfer_tx": int(parts[6]),
            })

    # Read server interface address
    try:
        address = await _run("ip -4 addr show wg0 | grep inet | awk '{print $2}'")
    except Exception:
        address = "10.100.0.1/24"

    return {
        "active": True,
        "server_public_key": server_public_key,
        "listen_port": int(listen_port),
        "address": address,
        "peers": peers,
    }
