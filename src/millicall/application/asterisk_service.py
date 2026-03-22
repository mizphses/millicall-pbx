import logging

from sqlalchemy.ext.asyncio import AsyncSession

from millicall.infrastructure.asterisk.config_writer import AsteriskConfigWriter
from millicall.infrastructure.asterisk.reloader import AsteriskReloader
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository

logger = logging.getLogger(__name__)


class AsteriskService:
    def __init__(self, session: AsyncSession):
        self.extension_repo = ExtensionRepository(session)
        self.peer_repo = PeerRepository(session)
        self.config_writer = AsteriskConfigWriter()
        self.reloader = AsteriskReloader()

    async def apply_config(self, notify_endpoints: list[str] | None = None) -> None:
        """Regenerate all Asterisk configs from DB and reload.

        If notify_endpoints is provided, send check-sync NOTIFY to those endpoints.
        If None, send to all registered endpoints.
        """
        extensions = await self.extension_repo.get_all()
        peers = await self.peer_repo.get_all()

        peer_map = {p.id: p for p in peers if p.id is not None}

        self.config_writer.write_pjsip_config(peers)
        self.config_writer.write_extensions_config(extensions, peer_map)

        logger.info("Asterisk config generated, reloading...")
        self.reloader.reload_all()
        logger.info("Asterisk reload complete")

        # Send check-sync to phones so they re-download provisioning config
        targets = notify_endpoints if notify_endpoints is not None else [p.username for p in peers]
        if targets:
            logger.info("Sending check-sync to: %s", targets)
            self.reloader.send_check_sync_all(targets)
