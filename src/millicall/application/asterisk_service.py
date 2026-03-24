import logging

from sqlalchemy.ext.asyncio import AsyncSession

from millicall.infrastructure.asterisk.config_writer import AsteriskConfigWriter
from millicall.infrastructure.asterisk.reloader import AsteriskReloader
from millicall.infrastructure.repositories.device_repo import DeviceRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository
from millicall.infrastructure.repositories.trunk_repo import TrunkRepository

logger = logging.getLogger(__name__)


class AsteriskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.extension_repo = ExtensionRepository(session)
        self.peer_repo = PeerRepository(session)
        self.trunk_repo = TrunkRepository(session)
        self.device_repo = DeviceRepository(session)
        self.config_writer = AsteriskConfigWriter()
        self.reloader = AsteriskReloader()

    async def apply_config(self, notify_endpoints: list[str] | None = None) -> None:
        """Regenerate all Asterisk configs from DB and reload."""
        extensions = await self.extension_repo.get_all()
        peers = await self.peer_repo.get_all()
        trunks = await self.trunk_repo.get_all_enabled()

        peer_map = {p.id: p for p in peers if p.id is not None}

        self.config_writer.write_pjsip_config(peers, trunks=trunks)
        self.config_writer.write_extensions_config(extensions, peer_map, trunks=trunks)
        self.config_writer.write_ari_config()

        logger.info("Asterisk config generated, reloading...")
        self.reloader.reload_all()
        logger.info("Asterisk reload complete")

        # SIP NOTIFY check-sync (works if phone is registered)
        targets = notify_endpoints if notify_endpoints is not None else [p.username for p in peers]
        if targets:
            logger.info("Sending SIP check-sync to: %s", targets)
            self.reloader.send_check_sync_all(targets)

        # HTTP resync to device IPs (works even if phone isn't SIP-registered)
        devices = await self.device_repo.get_all()
        device_ips = [d.ip_address for d in devices if d.ip_address and d.provisioned]
        if device_ips:
            logger.info("Sending HTTP resync to devices: %s", device_ips)
            self.reloader.send_resync_to_devices(device_ips)
