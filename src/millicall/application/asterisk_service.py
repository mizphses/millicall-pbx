import logging

from sqlalchemy.ext.asyncio import AsyncSession

from millicall.infrastructure.asterisk.config_writer import AsteriskConfigWriter, TrunkConfig
from millicall.infrastructure.asterisk.reloader import AsteriskReloader
from millicall.infrastructure.repositories.ai_agent_repo import AIAgentRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository
from millicall.infrastructure.repositories.settings_repo import SettingsRepository

logger = logging.getLogger(__name__)


class AsteriskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.extension_repo = ExtensionRepository(session)
        self.peer_repo = PeerRepository(session)
        self.config_writer = AsteriskConfigWriter()
        self.reloader = AsteriskReloader()

    async def _load_trunk_config(self) -> TrunkConfig:
        repo = SettingsRepository(self.session)
        s = await repo.get_all()
        return TrunkConfig(
            enabled=s.get("trunk_enabled", "N").upper() in ("Y", "YES", "TRUE", "1"),
            host=s.get("trunk_host", "192.168.1.1"),
            username=s.get("trunk_username", "0003"),
            password=s.get("trunk_password", ""),
            did_number=s.get("trunk_did_number", ""),
            caller_id=s.get("trunk_caller_id", ""),
            incoming_dest=s.get("trunk_incoming_dest", ""),
        )

    async def apply_config(self, notify_endpoints: list[str] | None = None) -> None:
        """Regenerate all Asterisk configs from DB and reload."""
        extensions = await self.extension_repo.get_all()
        peers = await self.peer_repo.get_all()
        ai_agent_repo = AIAgentRepository(self.session)
        ai_agents = await ai_agent_repo.get_all()
        trunk = await self._load_trunk_config()

        peer_map = {p.id: p for p in peers if p.id is not None}

        self.config_writer.write_pjsip_config(peers, trunk=trunk)
        self.config_writer.write_extensions_config(extensions, peer_map, ai_agents, trunk)

        logger.info("Asterisk config generated, reloading...")
        self.reloader.reload_all()
        logger.info("Asterisk reload complete")

        targets = notify_endpoints if notify_endpoints is not None else [p.username for p in peers]
        if targets:
            logger.info("Sending check-sync to: %s", targets)
            self.reloader.send_check_sync_all(targets)
