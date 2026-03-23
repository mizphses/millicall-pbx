"""Generate phone provisioning config files (Panasonic KX-HDV, Yealink)."""

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
            'CFG_RESYNC_FROM_SIP="Y"',
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
        mac_colon = ":".join(mac_clean[i : i + 2] for i in range(0, 12, 2))

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
            "# Registration",
            'REG_EXPIRE_TIME_1="300"',
            "",
            "# Display",
            f'DISPLAY_NAME_1="{extension.display_name}"',
            "",
            "# Codec Settings - Line 1",
            "# Enable PCMU (G.711u)",
            'CODEC_ENABLE4_1="Y"',
            'CODEC_PRIORITY4_1="1"',
            "# Enable PCMA (G.711a)",
            'CODEC_ENABLE1_1="Y"',
            'CODEC_PRIORITY1_1="2"',
            "",
        ]
        return "\r\n".join(lines) + "\r\n"

    # ── Yealink provisioning ──────────────────────────────────────

    def generate_yealink_boot(self) -> str:
        """Generate y000000000000.boot — tells all Yealink phones where to find configs."""
        lines = [
            "#!version:1.0.0.1",
            "",
            f"include:config <http://{PBX_ADDR}:8000/provisioning/Yealink/common.cfg>",
            f'include:config "http://{PBX_ADDR}:8000/provisioning/Yealink/{{{{mac}}}}.cfg"',
            "",
            "overwrite_mode = 1",
            "specific_model.excluded_mode = 0",
        ]
        return "\n".join(lines) + "\n"

    def generate_yealink_common_config(self) -> str:
        """Generate common.cfg shared by all Yealink phones."""
        lines = [
            "#!version:1.0.0.1",
            "",
            "## Millicall PBX - Yealink Common Configuration",
            "",
            "## Auto Provisioning",
            f"static.auto_provision.server.url = http://{PBX_ADDR}:8000/provisioning/Yealink",
            "static.auto_provision.power_on = 1",
            "static.auto_provision.repeat.enable = 1",
            "static.auto_provision.repeat.minutes = 1440",
            "",
            "## NTP / Timezone (Asia/Tokyo, +9)",
            f"local_time.ntp_server1 = {PBX_ADDR}",
            "local_time.time_zone = +9",
            "local_time.time_zone_name = Japan",
            "local_time.summer_time = 0",
            "local_time.date_format = 2",
            "local_time.time_format = 1",
            "",
            "## Language",
            "lang.gui = Japanese",
            "lang.wui = Japanese",
            "",
            "## Tone - Japanese",
            "voice.tone.dial = 400/0",
            "voice.tone.busy = 400/500,0/500",
            "voice.tone.ring = 400+15/1000,0/2000",
            "",
        ]
        return "\n".join(lines) + "\n"

    async def generate_yealink_device_config(self, mac_address: str) -> str | None:
        """Generate {mac}.cfg for a specific Yealink phone."""
        mac_clean = mac_address.upper().replace(":", "").replace("-", "").replace(".", "")
        mac_colon = ":".join(mac_clean[i : i + 2] for i in range(0, 12, 2))

        device = await self.device_repo.get_by_mac(mac_colon)
        if not device or not device.peer_id or not device.extension_id:
            return None

        peer = await self.peer_repo.get_by_id(device.peer_id)
        extension = await self.extension_repo.get_by_id(device.extension_id)

        if not peer or not extension:
            return None

        lines = [
            "#!version:1.0.0.1",
            "",
            f"## Millicall PBX - Config for {mac_colon}",
            f"## Extension: {extension.number} ({extension.display_name})",
            "",
            "## Account 1 - Registration",
            "account.1.enable = 1",
            f"account.1.label = {extension.number}",
            f"account.1.display_name = {extension.display_name}",
            f"account.1.auth_name = {peer.username}",
            f"account.1.user_name = {peer.username}",
            f"account.1.password = {peer.password}",
            f"account.1.sip_server.1.address = {PBX_ADDR}",
            "account.1.sip_server.1.port = 5060",
            "account.1.sip_server.1.transport_type = 0",
            "account.1.sip_server.1.expires = 300",
            "",
            "## Codec (G.711u priority 1, G.711a priority 2)",
            "account.1.codec.pcmu.enable = 1",
            "account.1.codec.pcmu.priority = 1",
            "account.1.codec.pcma.enable = 1",
            "account.1.codec.pcma.priority = 2",
            "account.1.codec.g722.enable = 1",
            "account.1.codec.g722.priority = 3",
            "account.1.codec.g729.enable = 0",
            "",
            "## NAT",
            "account.1.nat.nat_traversal = 0",
            "account.1.nat.udp_update_enable = 1",
            "account.1.nat.udp_update_time = 30",
            "account.1.nat.rport = 1",
            "",
            "## DTMF (RFC2833)",
            "account.1.dtmf.type = 1",
            "account.1.dtmf.dtmf_payload = 101",
            "",
        ]
        return "\n".join(lines) + "\n"
