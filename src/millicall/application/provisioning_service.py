"""Generate Panasonic KX-HDV phone provisioning config files."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from millicall.config import settings
from millicall.infrastructure.repositories.device_repo import DeviceRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository

logger = logging.getLogger(__name__)

PBX_ADDR = settings.pbx_bind_address
if PBX_ADDR == "0.0.0.0":
    PBX_ADDR = "172.20.0.1"


class ProvisioningService:
    def __init__(self, session: AsyncSession):
        self.device_repo = DeviceRepository(session)
        self.peer_repo = PeerRepository(session)
        self.extension_repo = ExtensionRepository(session)

    def generate_common_config(self) -> str:
        """Generate ConfigCommon.cfg for all phones (master config)."""
        lines = [
            "# Panasonic SIP Phone Standard Format File #",
            "# DO NOT CHANGE THIS LINE!",
            "",
            "# Millicall PBX - Common Configuration",
            "",
            "# Provisioning",
            f'CFG_STANDARD_FILE_PATH="http://{PBX_ADDR}:8000/provisioning/Panasonic/Config{{MAC}}.cfg"',
            f'CFG_MASTER_FILE_PATH="http://{PBX_ADDR}:8000/provisioning/Panasonic/ConfigCommon.cfg"',
            'CFG_RESYNC_TIME="02:00"',
            "",
            "# NTP",
            f'NTP_ADDR="{PBX_ADDR}"',
            'TIME_ZONE="GMT +9:00"',
            'DST_ENABLE="N"',
            "",
            "# Language",
            'DEFAULT_LANGUAGE="jp"',
            'WEB_LANGUAGE="jp"',
            "",
            "# DNS SRV disabled",
            'SIP_DNSSRV_ENA_1="N"',
            'SIP_DNSSRV_ENA_2="N"',
            "",
            "# Dial tone - Japanese 400Hz continuous",
            'DIAL_TONE_FRQ="400"',
            'DIAL_TONE_TIMING="0"',
            "",
            "# Busy tone - Japanese",
            'BUSY_TONE_FRQ="400"',
            'BUSY_TONE_TIMING="500/500"',
            "",
            "# Ringback tone - Japanese",
            'RINGBACK_TONE_FRQ="400+15"',
            'RINGBACK_TONE_TIMING="1000/2000"',
            "",
        ]
        return "\r\n".join(lines) + "\r\n"

    async def generate_device_config(self, mac_address: str) -> str | None:
        """Generate Config{MAC}.cfg for a specific phone."""
        mac_clean = mac_address.upper().replace(":", "").replace("-", "").replace(".", "")
        mac_colon = ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))

        device = await self.device_repo.get_by_mac(mac_colon)
        if not device or not device.peer_id or not device.extension_id:
            return None

        peer = await self.peer_repo.get_by_id(device.peer_id)
        extension = await self.extension_repo.get_by_id(device.extension_id)

        if not peer or not extension:
            return None

        lines = [
            "# Panasonic SIP Phone Standard Format File #",
            "# DO NOT CHANGE THIS LINE!",
            "",
            f"# Millicall PBX - Config for {mac_colon}",
            f"# Extension: {extension.number} ({extension.display_name})",
            "",
            "# SIP Settings - Line 1",
            f'PHONE_NUMBER_1="{extension.number}"',
            f'SIP_RGSTR_ADDR_1="{PBX_ADDR}"',
            'SIP_RGSTR_PORT_1="5060"',
            f'SIP_PRXY_ADDR_1="{PBX_ADDR}"',
            'SIP_PRXY_PORT_1="5060"',
            f'SIP_OUTPROXY_ADDR_1="{PBX_ADDR}"',
            'SIP_OUTPROXY_PORT_1="5060"',
            f'SIP_SVCDOMAIN_1="{PBX_ADDR}"',
            f'SIP_AUTHID_1="{peer.username}"',
            f'SIP_PASS_1="{peer.password}"',
            f'SIP_URI_1="{peer.username}"',
            'SIP_DNSSRV_ENA_1="N"',
            "",
            "# Codec Settings - Line 1",
            '# Enable PCMU (G.711u)',
            'CODEC_ENABLE4_1="Y"',
            'CODEC_PRIORITY4_1="1"',
            '# Enable PCMA (G.711a)',
            'CODEC_ENABLE1_1="Y"',
            'CODEC_PRIORITY1_1="2"',
            "",
        ]
        return "\r\n".join(lines) + "\r\n"
